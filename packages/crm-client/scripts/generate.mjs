#!/usr/bin/env node
/**
 * Generate OpenAPI schema snapshot + TypeScript types for @fast-plan/crm-client.
 *
 * Modes:
 *   1) From live URL:
 *        node scripts/generate.mjs --schema http://127.0.0.1:8000/api/schema/
 *   2) From Django spectacular (no server; run from repo with PYTHONPATH):
 *        node scripts/generate.mjs --spectacular
 *   3) Types only (schema already present):
 *        node scripts/generate.mjs --types-only
 */
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkgRoot = join(__dirname, "..");
const repoRoot = join(pkgRoot, "..", "..");
const outDir = join(pkgRoot, "generated");
const schemaPath = join(outDir, "openapi-schema.json");
const typesPath = join(outDir, "schema.d.ts");

const args = process.argv.slice(2);
const schemaIdx = args.indexOf("--schema");
const schemaUrl =
  (schemaIdx >= 0 ? args[schemaIdx + 1] : null) ||
  process.env.FAST_PLAN_SCHEMA_URL ||
  "";
const useSpectacular = args.includes("--spectacular");
const typesOnly = args.includes("--types-only");

mkdirSync(outDir, { recursive: true });

async function fetchSchema(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch schema: HTTP ${res.status} from ${url}`);
  }
  return await res.text();
}

function dumpSpectacular() {
  const backend = join(repoRoot, "backend");
  const result = spawnSync(
    process.env.PYTHON || "python",
    ["manage.py", "spectacular", "--file", schemaPath],
    {
      cwd: backend,
      encoding: "utf8",
      env: {
        ...process.env,
        DJANGO_SETTINGS_MODULE: "config.settings",
        DJANGO_SECRET_KEY:
          process.env.DJANGO_SECRET_KEY ||
          "ci-openapi-secret-key-at-least-32-characters",
        DJANGO_DEBUG: process.env.DJANGO_DEBUG || "true",
      },
    },
  );
  if (result.status !== 0) {
    console.error(result.stdout || "");
    console.error(result.stderr || "");
    throw new Error(`manage.py spectacular failed with exit ${result.status}`);
  }
  console.log(`Wrote ${schemaPath} via spectacular`);
}

function generateTypes() {
  if (!existsSync(schemaPath)) {
    throw new Error(`Missing ${schemaPath}; run with --schema or --spectacular first`);
  }
  const result = spawnSync(
    "npx",
    ["--yes", "openapi-typescript", schemaPath, "-o", typesPath],
    { cwd: pkgRoot, encoding: "utf8", shell: true },
  );
  if (result.status !== 0) {
    console.error(result.stdout || "");
    console.error(result.stderr || "");
    throw new Error(`openapi-typescript failed with exit ${result.status}`);
  }
  const size = readFileSync(typesPath, "utf8").length;
  if (size < 50) {
    throw new Error(`Generated types look empty (${size} bytes)`);
  }
  console.log(`Wrote ${typesPath} (${size} bytes)`);
}

if (typesOnly) {
  generateTypes();
} else if (useSpectacular) {
  dumpSpectacular();
  generateTypes();
} else if (schemaUrl) {
  const text = await fetchSchema(schemaUrl);
  writeFileSync(schemaPath, text);
  console.log(`Wrote ${schemaPath} (${text.length} bytes) from ${schemaUrl}`);
  generateTypes();
} else {
  // Default: spectacular if backend available, else require existing schema
  try {
    dumpSpectacular();
  } catch (err) {
    if (!existsSync(schemaPath)) {
      console.error(String(err));
      console.error(
        "Pass --schema <url>, --spectacular, or --types-only with an existing schema.",
      );
      process.exit(1);
    }
    console.warn("spectacular dump failed; using existing schema file");
  }
  generateTypes();
}
