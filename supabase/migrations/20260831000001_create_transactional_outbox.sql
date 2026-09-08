-- XTC LIVE V13-RC2: transactional outbox + webhook_events base table
-- Publishes the physical base table (not a view) for Supabase Realtime /
-- PostgreSQL logical replication. RLS enforces client isolation.
-- JSONB `type` is extracted to a generated column for efficient filtering.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Durable webhook ingress ledger (idempotent by event_id)
CREATE TABLE IF NOT EXISTS public.webhook_events (
    id              BIGSERIAL PRIMARY KEY,
    event_id        TEXT NOT NULL,
    provider        TEXT NOT NULL DEFAULT 'revenuecat',
    payload         JSONB NOT NULL,
    -- Extract JSONB type for indexing / filtering (fixes prior syntax defect)
    event_type      TEXT GENERATED ALWAYS AS (payload ->> 'type') STORED,
    signature_kid   TEXT,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'received'
                    CHECK (status IN ('received', 'processed', 'duplicate', 'rejected', 'dlq')),
    error_reason    TEXT,
    CONSTRAINT webhook_events_event_id_unique UNIQUE (event_id)
);

CREATE INDEX IF NOT EXISTS webhook_events_status_idx
    ON public.webhook_events (status, received_at);

CREATE INDEX IF NOT EXISTS webhook_events_type_idx
    ON public.webhook_events (event_type);

-- Transactional outbox (Year-One: PG + Redis/BullMQ; Phase 2 → Kafka @ >10k eps)
CREATE TABLE IF NOT EXISTS public.outbox_events (
    id              BIGSERIAL PRIMARY KEY,
    aggregate_type  TEXT NOT NULL,
    aggregate_id    TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    available_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at       TIMESTAMPTZ,
    locked_by       TEXT,
    attempts        INT NOT NULL DEFAULT 0,
    published_at    TIMESTAMPTZ,
    CONSTRAINT outbox_events_dedupe UNIQUE (aggregate_type, aggregate_id, event_type, created_at)
);

CREATE INDEX IF NOT EXISTS outbox_events_poll_idx
    ON public.outbox_events (available_at, id)
    WHERE published_at IS NULL;

-- Worker claim helper: FOR UPDATE SKIP LOCKED concurrency control
CREATE OR REPLACE FUNCTION public.claim_outbox_batch(
    p_worker_id TEXT,
    p_batch_size INT DEFAULT 50
)
RETURNS SETOF public.outbox_events
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH cte AS (
        SELECT id
        FROM public.outbox_events
        WHERE published_at IS NULL
          AND available_at <= now()
          AND (locked_at IS NULL OR locked_at < now() - INTERVAL '5 minutes')
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT p_batch_size
    )
    UPDATE public.outbox_events o
    SET locked_at = now(),
        locked_by = p_worker_id,
        attempts  = o.attempts + 1
    FROM cte
    WHERE o.id = cte.id
    RETURNING o.*;
END;
$$;

-- Dead-letter queue with deterministic PII masking expectation (app-layer)
CREATE TABLE IF NOT EXISTS public.webhook_dlq (
    id              BIGSERIAL PRIMARY KEY,
    event_id        TEXT,
    masked_payload  JSONB NOT NULL,
    reason          TEXT NOT NULL,
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: clients must not read raw webhook_events without privileged role
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_dlq ENABLE ROW LEVEL SECURITY;

-- service_role exists on Supabase; skip policies when role is absent (local PG)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        EXECUTE 'DROP POLICY IF EXISTS webhook_events_service_all ON public.webhook_events';
        EXECUTE $p$
            CREATE POLICY webhook_events_service_all
                ON public.webhook_events
                FOR ALL
                TO service_role
                USING (true)
                WITH CHECK (true)
        $p$;
        EXECUTE 'DROP POLICY IF EXISTS outbox_events_service_all ON public.outbox_events';
        EXECUTE $p$
            CREATE POLICY outbox_events_service_all
                ON public.outbox_events
                FOR ALL
                TO service_role
                USING (true)
                WITH CHECK (true)
        $p$;
    END IF;
END $$;

-- Publish BASE TABLE (not a sanitized view) — logical replication requires relations
-- that are physical tables. Views throw runtime relation errors.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) THEN
        CREATE PUBLICATION supabase_realtime FOR TABLE public.webhook_events;
    ELSE
        BEGIN
            ALTER PUBLICATION supabase_realtime DROP TABLE public.webhook_events;
        EXCEPTION WHEN undefined_object THEN
            NULL; -- table was not in publication
        END;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.webhook_events;
    END IF;
END $$;

COMMIT;
