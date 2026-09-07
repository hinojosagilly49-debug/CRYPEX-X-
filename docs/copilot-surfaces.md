# Copilot surfaces on CRYPEX-X-

How GitHub Copilot features relate to this repository. Preview products may change.

## Assistive (human-led)

| Feature | Use here |
|---------|----------|
| Inline / next-edit suggestions | Edit `src/cryptex_x/`, tests, GTM docs while typing |
| Chat (Ask / Edit) | Explain hop logs, SARC-DQ, PreFlect holds; small scoped edits |
| PR summaries | Summarize PRs once opened from agent branches |
| GitHub Desktop commit messages | Local commits from the diff |

## Agentic (goal-led)

| Feature | Use here |
|---------|----------|
| **Cloud agent** (`/tasks/`) | **Primary path used so far** — research → plan → branch (e.g. `copilot/focus-next-steps`); PR optional |
| IDE Agent mode | Local multi-file loops against metals-desk package |
| Copilot CLI | Terminal agent; `/delegate` can hand off to cloud |
| Copilot app | Parallel sessions / worktrees / cloud sessions |
| Code review | Review comments after a PR exists |
| Agentic Workflows (preview) | Markdown → Actions jobs; **not configured** (no `.github/` workflows) |
| 3rd-party coding agents (preview) | Same cloud sandbox model as cloud agent |

## CRYPEX-X- policy (current)

- Product and pilot packaging work: **cloud coding agent** (branch/PR).
- **No** custom Agentic Workflow `.md` / `.lock.yml` jobs yet.
- Acceptance gate remains local/CI: `pip install -e ".[dev]" && pytest -q` (A1–A8).

## Customization (any surface)

Spaces, custom instructions, Memory, prompt files, MCP, agent skills, and custom agents can steer assistive or agentic runs. Repo Memory should stay aligned with pipeline routing and the acceptance test command.

## Related docs

- [GTM one-pager](gtm/one-pager.md)
- [Pilot SOW (A1–A8)](gtm/pilot-sow.md)
- [Crypto agility](security/crypto-agility.md)
