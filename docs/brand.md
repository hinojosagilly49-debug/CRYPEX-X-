# Meridian brand assets

Industrial metals & freight desk identity for CRYPEX-X- / Meridian share surfaces.

## Files

| Asset | Path | Spec |
|-------|------|------|
| Share card | `public/og.jpg` | 1200×630 JPEG, centered **MERIDIAN** / **METALS & FREIGHT** lockup over cryptex envelope, copper plate, aluminium coil, hairline ledger |
| Favicon | `public/favicon.svg` | Filled steel-paper globe + dark meridian on near-black ink, slate hairline frame (legible at 16px) |
| Site meta | `src/lib/og/site.json` | `{ "title": "Meridian", "type": "website", "card": "custom" }` |

**Not included:** `x-banner.jpg` (not a game), PWA raster icons (not requested).

## Check

```bash
node scripts/brand-check.mjs
```

Expect `ok: true`, `warnings: []` (or only non-blocking notes).

## Regenerate OG card

```bash
pip install pillow
python scripts/generate_og_card.py
node scripts/brand-check.mjs
```

## Palette (industrial)

| Token | Hex | Use |
|-------|-----|-----|
| Ink | `#0c0e12` | Field / meridian |
| Slate | `#464e5a` | Hairline frame |
| Steel paper | `#c6ccd4` | Globe fill |
| Copper | `#b0683e` | Seal / accent |
