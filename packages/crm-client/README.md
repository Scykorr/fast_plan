# @fast-plan/crm-client

Typed CRM client for Fast Plan integrators (v0.17.0).

## Install (workspace / private)

```bash
cd packages/crm-client
npm install
npm run build
```

## Usage

```ts
import { createCrmClient } from "@fast-plan/crm-client";

const crm = createCrmClient({
  baseUrl: "https://your-host",
  token: process.env.FP_API_TOKEN,
  workspaceId: 1,
});

const orgs = await crm.listOrganizations();
const fields = await crm.getEntityCustomFields("person", 42);
await crm.putEntityCustomFields("person", 42, { vip: true });
```

## OpenAPI + codegen

Backend exposes:

- `GET /api/schema/` — OpenAPI 3 (drf-spectacular)
- `GET /api/docs/` — Swagger UI

Generate schema + `generated/schema.d.ts`:

```bash
# from Django (no server)
npm run generate -- --spectacular

# or from a live URL
npm run generate -- --schema http://127.0.0.1:8000/api/schema/

# types only
npm run generate -- --types-only
```

CI job `openapi-sdk` regenerates schema + runs `openapi-typescript` on every push.
Import generated types via `@fast-plan/crm-client/schema` when published from `generated/schema.d.ts`.
