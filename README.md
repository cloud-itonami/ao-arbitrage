# arbitrage

`cloud-itonami/arbitrage` — **educational cross-asset arbitrage *signal* feed.**
It proposes, posts, and mentions. **It never executes.**

The name says what the subject is, not what the code does. What the code
actually is today is small and worth stating plainly: **one Cloudflare Worker
that is a thin edge facade.** It holds no strategy, no market data, and no
position. Every arbitrage decision it exists to surface is computed somewhere
else and arrives over XRPC.

| | |
|---|---|
| repo | `cloud-itonami/arbitrage` (west path `orgs/cloud-itonami/arbitrage`) |
| origin | extracted from `etzhayyim/root` at `60-apps/etzhayyim-project-arbitrage` |
| runtime | Cloudflare Worker (SvelteKit + `@sveltejs/adapter-cloudflare`) |
| declared hosts | `arb.etzhayyim.com`, `arb2x301.etzhayyim.com` |
| deployed | **no** — see [Current status](#current-status) |
| tracked files | 13 |

## What it refuses to do

This is the load-bearing part of the repo, and it is declared in data rather
than enforced in code, so it is worth reading before anything else.

`worker/kotodama.jsonld` sets `complianceFrameworks: ["NoExecution",
"EducationalOnly"]` and states the boundary in the agent's own system prompt:

> You PROPOSE, POST, and MENTION only — you NEVER execute trades. You have no
> broker bindings, no exchange API keys, no order routing.

That claim is currently true by *absence*: there is no broker client, no
signing key, no order type, and no credential binding anywhere in the 13 tracked
files — the only outbound call in the repo is a POST to an MCP router
(`worker/svelte/src/routes/xrpc/[...path]/+server.ts`). Nothing in the repo
*asserts* the boundary; nothing tests it either. If execution is ever added
upstream, this repo will not notice.

Data sources named in the same file are public delayed/EOD feeds only (Yahoo
Finance, Stooq, JPX, CME, LME, CoinGecko, REIT.com, MLIT 地価公示, FRED), and
mentions are restricted to the opt-in cohort handle `@trader.etzhayyim.com`.

## Where the code actually runs

**There are two worker entry points in this repo and only one of them ships.**
This is the single most misleading thing about the file layout, so it is stated
here rather than left to be discovered:

```
worker/wrangler.jsonc
  main: "svelte/.svelte-kit/cloudflare/_worker.js"   ← the SvelteKit build output
```

- **`worker/svelte/` — this is what deploys.** `main` points at the
  adapter-cloudflare build output. Its routes are `/` (a scaffold status page)
  and `POST /xrpc/<nsid>` (proxy to the MCP router).
- **`worker/src/app.ts` — this does not deploy.** It is a hand-written facade
  with its own `/health` endpoint and a *different* upstream
  (`dispatcher.etzhayyim.com` rather than `mcp.etzhayyim.com`). No build
  references it, no `tsconfig.json` covers it, and it does not typecheck on its
  own (`ExportedHandler` needs `@cloudflare/workers-types`, which is not a
  dependency here). Verified against a real build in
  [`docs/operator-quickstart.md`](docs/operator-quickstart.md) §3.

Deciding which of the two is authoritative is a design change, not a
documentation change, so this README only records that they disagree.

## Repository layout

```
PROJECT.jsonld            project identity + the 10 declared actor DIDs
README.edn                extraction record (machine-readable, superseded as an entry point by this file)
migration.edn             what was extracted from etzhayyim/root, with a checkable byte count
worker/
  kotodama.jsonld         agent identity, KPIs, governance, channels, triggers
  wrangler.jsonc          Cloudflare config — routes, vars, and `main`
  src/app.ts              unbuilt second facade (see above)
  svelte/                 the deployed worker
    src/routes/+page.svelte              status page at /
    src/routes/xrpc/[...path]/+server.ts POST /xrpc/<nsid> → MCP router
```

`migration.edn` claims the extraction carried **11 files / 15,234 bytes**. That
is still exactly true of the 11 non-metadata files in this repo, and
[`docs/operator-quickstart.md`](docs/operator-quickstart.md) §2 checks it in one
command with no dependencies installed.

## Current status

**Nothing here is live, and the upstream it talks to does not exist yet.**
Measured 2026-08-12:

| host | role | resolves |
|---|---|---|
| `etzhayyim.com` | parent zone | yes (Cloudflare) |
| `arb.etzhayyim.com` | declared route + `did:web` base | **no** |
| `arb2x301.etzhayyim.com` | declared route | **no** |
| `mcp.etzhayyim.com` | upstream the shipped route proxies to | **no** |
| `dispatcher.etzhayyim.com` | upstream `src/app.ts` would use | **no** |

Consequences that follow from that table:

- `POST /xrpc/<nsid>` returns **500 `{"message":"Internal Error"}`** even
  locally, because the upstream fetch throws and the route has no `try`/`catch`
  around it. The route's own error shapes (400 / 502) are unreachable while the
  router is down.
- The 10 actor DIDs in `PROJECT.jsonld` are all `did:web:arb.etzhayyim.com…`,
  which resolve through `https://arb.etzhayyim.com/.well-known/did.json`. **None
  of them resolve today.**
- The business logic the facade exists to reach — BPMN contracts under
  `com/etzhayyim/arb` and the Python `kotodama.ingest.arbitrage` module, both
  named in `worker/src/app.ts` — lives in `etzhayyim/root` and was **not**
  extracted into this repo. This repo cannot produce a signal on its own.

The build, the typecheck, and the local page all work. What is missing is
everything on the other side of the network boundary.

## Getting started

Read [`docs/operator-quickstart.md`](docs/operator-quickstart.md). It is written
so that §1–§2 need nothing installed, and §3 onward were each run end to end on
2026-08-12 with their real output recorded, including the failures.

## Naming

The bare name `arbitrage` is the **subject** plane: this is not a mirror of an
external spec, and its executing role is not yet fixed. Identity is the path
`cloud-itonami/arbitrage`, not the name alone.

Note that `README.edn` still records the pre-extraction destination
`etzhayyim/com-etzhayyim-app-arbitrage`, and every DID, host, and namespace in
this repo is under `etzhayyim.com`. The code has moved orgs; the identifiers
have not. Reconciling them is a governance decision, not a rename.
