# ao-arbitrage

`cloud-itonami/ao-arbitrage` (renamed from `arbitrage` on 2026-09-24) —
**educational cross-asset arbitrage *signal* feed, and the resident bot that
measures and proposes it.** It proposes, posts, and mentions. **It never executes.**

The subject and the bot are one repository. The Hermes profile that acts for
it — `awai-arb` — lives in [`hermes/`](hermes/README.md) and is materialized
onto the host from there.

The name says what the subject is, not what the code does. What the code
actually is today is small and worth stating plainly: **one Cloudflare Worker
that is a thin edge facade.** It holds no strategy, no market data, and no
position. Every arbitrage decision it exists to surface is computed somewhere
else and arrives over XRPC.

| | |
|---|---|
| repo | `cloud-itonami/ao-arbitrage` (west path `orgs/cloud-itonami/ao-arbitrage`) |
| origin | extracted from `etzhayyim/root` at `60-apps/etzhayyim-project-arbitrage` |
| runtime | Cloudflare Worker (static assets from a ClojureScript/reagent/re-frame build — migrated from SvelteKit 2026-08-26, see below) |
| declared hosts | `arb.etzhayyim.com`, `arb2x301.etzhayyim.com` |
| deployed | **no** — see [Current status](#current-status) |
| tracked files | 12 (`PROJECT.jsonld` + `worker/`) |

## What it refuses to do

This is the load-bearing part of the repo, and it is declared in data rather
than enforced in code, so it is worth reading before anything else.

`worker/kotodama.jsonld` sets `complianceFrameworks: ["NoExecution",
"EducationalOnly"]` and states the boundary in the agent's own system prompt:

> You PROPOSE, POST, and MENTION only — you NEVER execute trades. You have no
> broker bindings, no exchange API keys, no order routing.

That claim is currently true by *absence*: there is no broker client, no
signing key, no order type, and no credential binding anywhere in this repo.
The only outbound call this repo has ever contained was a POST to an MCP
router, in a SvelteKit server route
(`worker/svelte/src/routes/xrpc/[...path]/+server.ts`). That route has been
preserved verbatim at [`worker/src/xrpc-proxy.ts`](worker/src/xrpc-proxy.ts) as part
of the 2026-08-26 Svelte→ClojureScript frontend migration (see
[Where the code actually runs](#where-the-code-actually-runs)), but it is
**not wired into any build or Worker entry point today** — the Worker now
serves static assets only, so this repo currently makes **no** outbound calls
at all, not even the ones that used to 500. Nothing in the repo *asserts* the
NoExecution boundary; nothing tests it either. If execution is ever added
upstream, this repo will not notice.

Data sources named in the same file are public delayed/EOD feeds only (Yahoo
Finance, Stooq, JPX, CME, LME, CoinGecko, REIT.com, MLIT 地価公示, FRED), and
mentions are restricted to the opt-in cohort handle `@trader.etzhayyim.com`.

## Where the code actually runs

**As of 2026-08-26 the frontend was migrated from SvelteKit to ClojureScript**
(reagent + re-frame + `jp-go-dds`, per this workspace's UI standard). Only the
`worker/svelte/` subtree — the status page and its build tooling — was in
scope for that migration; `worker/src/app.ts` was left untouched, and the
backend proxy route that used to live inside `worker/svelte/` was preserved
rather than deleted (see below). `worker/wrangler.jsonc` was updated to match,
but **`wrangler deploy`/`wrangler dev` were not run** — the change is
UNVERIFIED against a real Cloudflare account.

```
worker/wrangler.jsonc
  (no "main")   ← dropped; there is no server-rendered Worker script anymore
  assets.directory: "./cljs/public"   ← the ClojureScript build's static output
```

- **`worker/cljs/` — this is what deploys.** A shadow-cljs `:browser` build
  (reagent + re-frame view over `jp-go-dds` components) whose `public/`
  directory — including the committed, pre-generated `public/index.html` —
  is served as static assets via the `ASSETS` binding. There is no
  server-side route in this build; `not_found_handling` stays `"none"`.
- **`worker/src/app.ts` — this still does not deploy**, unchanged from
  before this migration. It is a hand-written facade with its own `/health`
  endpoint and a *different* upstream (`dispatcher.etzhayyim.com` rather than
  `mcp.etzhayyim.com`). No build references it, no `tsconfig.json` covers it,
  and it does not typecheck on its own (`ExportedHandler` needs
  `@cloudflare/workers-types`, which is not a dependency here). It was read
  again during this migration specifically to check whether it calls
  `env.ASSETS.fetch` (it does not — it has its own `fetch` handler and 404s on
  anything outside `/health` and `/xrpc/com.etzhayyim.apps.arb.*`), which is
  why `main` was dropped rather than repointed at it: a worker script that
  doesn't itself serve `ASSETS` would sit in front of the assets with nothing
  serving them. Verified against a real build in
  [`docs/operator-quickstart.md`](docs/operator-quickstart.md) §3 (pre-migration).
- **`worker/src/xrpc-proxy.ts` — preserved, not wired.** This is the SvelteKit
  server route (`worker/svelte/src/routes/xrpc/[...path]/+server.ts`) that
  used to proxy `POST /xrpc/<nsid>` to the MCP router. It was real edge logic,
  not frontend markup, and had no cljs counterpart to migrate to (the cljs
  build has no server-side target), so rather than deleting it silently it
  was moved verbatim with a header explaining its status. It needs its own
  `tsconfig.json` and a decision about whether/how to wire it into a real
  Worker entry point before it does anything again — same open question this
  README already records for `worker/src/app.ts`.

Deciding which (if either) of `worker/src/app.ts` / `worker/src/xrpc-proxy.ts` is
authoritative going forward is a design change, not a documentation change,
so this README only records that a decision is outstanding.

## Repository layout

```
hermes/                   resident bot profile(s) — source of truth, see hermes/README.md
PROJECT.jsonld            project identity + the 10 declared actor DIDs
README.edn                extraction record (machine-readable, superseded as an entry point by this file)
migration.edn             what was extracted from etzhayyim/root, with a checkable byte count (historical — see below)
worker/
  kotodama.jsonld         agent identity, KPIs, governance, channels, triggers
  wrangler.jsonc          Cloudflare config — routes, vars, and `assets.directory`
  src/app.ts              unbuilt second facade (see above)
  src/xrpc-proxy.ts       preserved-but-unwired MCP-router proxy (see above)
  cljs/                   the deployed worker (static assets)
    deps.edn, shadow-cljs.edn, package.json   build config (reagent + re-frame + jp-go-dds)
    src/arbitrage_worker/app.cljs             the status page, as a reagent view
    test/arbitrage_worker/app_test.cljs       cljs.test coverage for it
    public/index.html                         committed, pre-generated HTML shell (DADS CSS inlined)
```

`migration.edn` claims the **original 2026-08 extraction from `etzhayyim/root`**
carried 11 files / 15,234 bytes. That claim is about the extraction event, not
an invariant over all time: it was true through commit `412fa8a`, and the
2026-08-26 Svelte→ClojureScript migration intentionally changed the tracked
file set (deleted `worker/svelte/`, added `worker/cljs/` and
`worker/src/xrpc-proxy.ts`), so the counts in
[`docs/operator-quickstart.md`](docs/operator-quickstart.md) §2 no longer
match `migration.edn` as of this commit — **that mismatch is expected, not a
sign that extracted content was edited without updating the record.** See
that document's §2 for the current counts and how they were recomputed.

## Current status

**Nothing here is live, and the upstream it talks to does not exist yet.**
Measured 2026-08-12:

| host | role | resolves |
|---|---|---|
| `etzhayyim.com` | parent zone | yes (Cloudflare) |
| `arb.etzhayyim.com` | declared route + `did:web` base | **no** |
| `arb2x301.etzhayyim.com` | declared route | **no** |
| `mcp.etzhayyim.com` | upstream `worker/src/xrpc-proxy.ts` would proxy to, if wired | **no** |
| `dispatcher.etzhayyim.com` | upstream `src/app.ts` would use | **no** |

Consequences that follow from that table:

- Pre-migration, `POST /xrpc/<nsid>` returned **500
  `{"message":"Internal Error"}`** even locally, because the upstream fetch
  threw and the route had no `try`/`catch` around it. As of the 2026-08-26
  frontend migration that route is no longer part of the deployed Worker at
  all (see [Where the code actually runs](#where-the-code-actually-runs)), so
  this specific failure mode is currently moot — there is no `/xrpc/*` route
  being served, working or otherwise.
- The 10 actor DIDs in `PROJECT.jsonld` are all `did:web:arb.etzhayyim.com…`,
  which resolve through `https://arb.etzhayyim.com/.well-known/did.json`. **None
  of them resolve today.**
- The business logic the facade exists to reach — BPMN contracts under
  `com/etzhayyim/arb` and the Python `kotodama.ingest.arbitrage` module, both
  named in `worker/src/app.ts` — lives in `etzhayyim/root` and was **not**
  extracted into this repo. This repo cannot produce a signal on its own.

Pre-migration (SvelteKit), the build, the typecheck, and the local page all
worked. What was missing was everything on the other side of the network
boundary — that has not changed. Post-migration (ClojureScript), see
[`docs/operator-quickstart.md`](docs/operator-quickstart.md) §3 for the
2026-08-26 build/test record; `wrangler deploy`/`wrangler dev` remain
unverified either way.

## Getting started

Read [`docs/operator-quickstart.md`](docs/operator-quickstart.md). §1–§2 need
nothing installed and describe the pre-migration (2026-08-12) extraction
record; §3 has been updated for the 2026-08-26 Svelte→ClojureScript
migration, with its build/test output recorded including any failures; §4–§8
are pre-migration and now describe the SvelteKit build this repo no longer
has (kept for history, flagged inline).

## Naming

`ao-` is the role prefix for a repository that is an artificial organism — a
resident bot (kotoba-lang/ao model) whose subject, code and Hermes profile
live together. Identity is the path `cloud-itonami/ao-arbitrage`; GitHub
redirects the old `cloud-itonami/arbitrage`.

Note that `README.edn` still records the pre-extraction destination
`etzhayyim/com-etzhayyim-app-arbitrage`, and every DID, host, and namespace in
this repo is under `etzhayyim.com`. The code has moved orgs; the identifiers
have not. Reconciling them is a governance decision, not a rename.
