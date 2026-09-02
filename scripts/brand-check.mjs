#!/usr/bin/env node
/**
 * Meridian brand asset gate.
 * Pass criteria: og.jpg 1200×630, favicon.svg present, site.json identity, no game banner required.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

const warnings = [];
const errors = [];

function ok(cond, msg) {
  if (!cond) errors.push(msg);
}

function warn(cond, msg) {
  if (!cond) warnings.push(msg);
}

const ogPath = path.join(root, "public", "og.jpg");
const favPath = path.join(root, "public", "favicon.svg");
const sitePath = path.join(root, "src", "lib", "og", "site.json");
const bannerPath = path.join(root, "public", "x-banner.jpg");

ok(fs.existsSync(ogPath), "missing public/og.jpg");
ok(fs.existsSync(favPath), "missing public/favicon.svg");
ok(fs.existsSync(sitePath), "missing src/lib/og/site.json");

// x-banner and PWA rasters intentionally absent (not a game / not requested)
if (fs.existsSync(bannerPath)) {
  warnings.push(
    "unexpected public/x-banner.jpg (not required for Meridian website card)"
  );
}

let site = null;
if (fs.existsSync(sitePath)) {
  try {
    site = JSON.parse(fs.readFileSync(sitePath, "utf8"));
  } catch (e) {
    errors.push(`site.json parse error: ${e.message}`);
  }
}

if (site) {
  ok(
    site.title === "Meridian",
    `site.json title must be "Meridian" (got ${JSON.stringify(site.title)})`
  );
  ok(
    site.type === "website",
    `site.json type must be "website" (got ${JSON.stringify(site.type)})`
  );
  ok(
    site.card === "custom",
    `site.json card must be "custom" (got ${JSON.stringify(site.card)})`
  );
}

if (fs.existsSync(ogPath)) {
  const buf = fs.readFileSync(ogPath);
  ok(buf[0] === 0xff && buf[1] === 0xd8, "og.jpg must be JPEG (SOI marker)");
  let w = 0;
  let h = 0;
  let i = 2;
  while (i < buf.length - 9) {
    if (buf[i] !== 0xff) {
      i += 1;
      continue;
    }
    const marker = buf[i + 1];
    if (marker === 0xd9 || marker === 0xda) break;
    const len = (buf[i + 2] << 8) | buf[i + 3];
    if (marker >= 0xc0 && marker <= 0xc3) {
      h = (buf[i + 5] << 8) | buf[i + 6];
      w = (buf[i + 7] << 8) | buf[i + 8];
      break;
    }
    i += 2 + len;
  }
  ok(w === 1200 && h === 630, `og.jpg must be 1200×630 (got ${w}×${h})`);
  const kb = buf.length / 1024;
  if (kb > 250) {
    warnings.push(`og.jpg is large (${kb.toFixed(1)} KB); target ~67–150 KB`);
  }
  ok(buf.length > 10_000, "og.jpg seems empty/too small");
}

if (fs.existsSync(favPath)) {
  const svg = fs.readFileSync(favPath, "utf8");
  ok(/viewBox="0 0 32 32"/.test(svg), "favicon.svg should use viewBox 0 0 32 32");
  ok(/circle/i.test(svg), "favicon.svg should include a globe circle");
  ok(
    /#0c0e12|#b0683e|meridian/i.test(svg),
    "favicon.svg should use Meridian industrial palette"
  );
  ok(
    /fill="#c6ccd4"|fill="#C6CCD4"/i.test(svg),
    "favicon.svg globe should be filled (16px legibility)"
  );
}

const result = {
  ok: errors.length === 0,
  errors,
  warnings,
  assets: {
    og: fs.existsSync(ogPath) ? "public/og.jpg" : null,
    favicon: fs.existsSync(favPath) ? "public/favicon.svg" : null,
    site: fs.existsSync(sitePath) ? "src/lib/og/site.json" : null,
    xBanner: fs.existsSync(bannerPath) ? "public/x-banner.jpg" : null,
  },
};

console.log(JSON.stringify(result, null, 2));
process.exit(errors.length === 0 ? 0 : 1);
