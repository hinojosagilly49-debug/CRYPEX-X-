#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const srcDir = path.join(root, "src", "xtc-live");
const distDir = path.join(root, "dist");

fs.rmSync(distDir, { recursive: true, force: true });
fs.mkdirSync(distDir, { recursive: true });

for (const name of fs.readdirSync(srcDir)) {
  if (!name.endsWith(".js")) continue;
  fs.copyFileSync(path.join(srcDir, name), path.join(distDir, name));
}

const stamp = {
  product: "XTC-LIVE",
  version: "13-rc2",
  builtAt: new Date().toISOString(),
  status: "PRODUCTION_CANDIDATE",
};
fs.writeFileSync(path.join(distDir, "build-info.json"), JSON.stringify(stamp, null, 2));
console.log("build ok → dist/ (%s files)", fs.readdirSync(distDir).length);
