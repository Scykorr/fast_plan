#!/usr/bin/env node
// Verifies VERSION, frontend/package.json and frontend/src/version.ts agree on the
// same product version. Run from the repo root: `node scripts/check-version-sync.mjs`.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const rootDir = join(dirname(fileURLToPath(import.meta.url)), "..");

function readVersionFile() {
  return readFileSync(join(rootDir, "VERSION"), "utf8").trim();
}

function readPackageJsonVersion() {
  const raw = readFileSync(join(rootDir, "frontend", "package.json"), "utf8");
  return JSON.parse(raw).version;
}

function readAppVersion() {
  const raw = readFileSync(join(rootDir, "frontend", "src", "version.ts"), "utf8");
  const match = /APP_VERSION\s*=\s*"([^"]+)"/.exec(raw);
  if (!match) {
    throw new Error("Could not find APP_VERSION in frontend/src/version.ts");
  }
  return match[1];
}

const versions = {
  VERSION: readVersionFile(),
  "frontend/package.json": readPackageJsonVersion(),
  "frontend/src/version.ts": readAppVersion(),
};

const unique = new Set(Object.values(versions));

if (unique.size > 1) {
  console.error("Version mismatch detected:");
  for (const [source, version] of Object.entries(versions)) {
    console.error(`  ${source}: ${version}`);
  }
  process.exit(1);
}

console.log(`Version sync OK: ${versions.VERSION}`);
