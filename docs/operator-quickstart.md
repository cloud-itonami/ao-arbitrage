# Operator quickstart — `cloud-itonami/arbitrage`

> **2026-08-26 update:** the frontend was migrated from SvelteKit to
> ClojureScript (reagent + re-frame + `jp-go-dds`) — see
> [`../README.md`](../README.md#where-the-code-actually-runs). §1–§2 below
> have been refreshed for the new tracked-file set and are current. §3 has
> been replaced with the cljs build/test record. **§4–§8 are unchanged from
> 2026-08-12 and describe the SvelteKit build this repo no longer has** —
> they are kept for history (the failures they recorded, e.g. the DNS/500
> chain in §5–§6, are still true facts about the upstream network, just not
> about a route this Worker serves anymore) but every command in them that
> touches `worker/svelte/` will fail with "no such file or directory" if you
> try to run it today. `wrangler deploy`/`wrangler dev` were not run against
> the new build either — that remains unverified ground, same as before.

Every command in §1–§3 below was run end to end on **2026-08-26** against the
migration branch. Commands in §4–§8 were run on **2026-08-12** against commit
`412fa8a` on `main`, before the migration; the output shown there is what came
back then. Where a step failed, the failure is recorded rather than fixed —
see §7 for the (pre-migration) list of things this document did **not** claim
to have done.

Read [`../README.md`](../README.md) first if you have not: this repo has two
non-deploying worker facades (`worker/src/app.ts`, `worker/src/xrpc-proxy.ts`) and
one deploying static-asset build (`worker/cljs/`), which makes
[Where the code actually runs](../README.md#where-the-code-actually-runs) the
section people skip and then get confused by.

- §1 and §2 need **nothing installed** — not even Node.
- §3 needs **Node + npm** (Clojure CLI + the JVM for `public/index.html`
  regeneration, if you need to redo that step).
- §4–§8 (pre-migration, historical) needed Node + npm and about 270 MB of
  disk, for a build that no longer exists in this tree.

Timings are from an M-series Mac with a warm npm cache. Treat them as an order
of magnitude, not a benchmark.

---

## §1 Read the repo without installing anything

There are 17 tracked files (was 13, pre-migration). You can still hold the
whole thing in your head.

```bash
git ls-files
```

```
.gitignore
docs/operator-quickstart.md
migration.edn
PROJECT.jsonld
README.edn
README.md
worker/cljs/.gitignore
worker/cljs/deps.edn
worker/cljs/package.json
worker/cljs/public/index.html
worker/cljs/shadow-cljs.edn
worker/cljs/src/arbitrage_worker/app.cljk
worker/cljs/test/arbitrage_worker/app_test.cljk
worker/kotodama.jsonld
worker/src/app.ts
worker/wrangler.jsonc
worker/src/xrpc-proxy.ts
```

The files that carry all the meaning:

| file | what it decides |
|---|---|
| `worker/kotodama.jsonld` | the agent's identity, its KPIs, and the **NoExecution / EducationalOnly** boundary |
| `worker/wrangler.jsonc` | which hosts it answers on, and that it now serves `worker/cljs/public` as static assets (no `main`) |
| `worker/cljs/src/arbitrage_worker/app.cljk` | the status page, ported from the old SvelteKit route |
| `worker/src/xrpc-proxy.ts` | the only outbound call this repo has ever had — **preserved, not wired** as of 2026-08-26 |
| `PROJECT.jsonld` | the 10 actor DIDs this project claims |

## §2 Check the extraction record — no dependencies

`migration.edn` records what was carried out of `etzhayyim/root` **at
extraction time (commit `412fa8a`)**: `:tracked-files 11 :bytes 15234`. That
was still exactly checkable through 2026-08-12; the 2026-08-26
Svelte→ClojureScript migration intentionally changed the tracked set (see
§1), so re-running the same command today gives different, larger numbers —
that is expected drift from real, in-scope work, not silent editing of
extracted content. Recomputed today:

```bash
git ls-files PROJECT.jsonld worker | wc -l
git ls-files PROJECT.jsonld worker | xargs wc -c | tail -1
```

```
      12
   96594 total
```

(`worker/cljs/public/index.html` alone is ~74 KB — DADS CSS is inlined into
it rather than linked, per `jp-go-dds.page`'s no-external-requests default —
which accounts for nearly all of the byte-count growth.)

**Neither number matches `migration.edn` anymore, and that's expected as of
this commit** — see the note above §1. Through 2026-08-12 both numbers matched
`migration.edn` exactly, and *that* invariant ("if either number moves without
a recorded reason, someone edited extracted content silently") is what this
check was for; the 2026-08-26 migration is the recorded reason. If you need to
re-verify going forward, re-run this same command and diff the byte count
against the `96594` recorded here (not against `migration.edn`'s `15234`) —
this document's own recorded output is now the reference point until the next
recorded change.

> The paths are **selected**, not filtered. An earlier draft of this file
> excluded the two metadata files with `grep -v` instead, which was correct
> right up until this document was committed and the count silently became 15.
> Naming the extracted paths keeps the check valid no matter what
> repo-level files get added later.

## §3 Build the worker that actually deploys (2026-08-26, ClojureScript)

```bash
cd worker/cljs
npm install
```

```
added 129 packages, and audited 130 packages in 19s

27 packages are looking for funding
  run `npm fund` for details

6 low severity vulnerabilities

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
```

Build, through the shared fleet resource guard (foreground, retried on
`exit 2` = lock held by another agent's build — this happened five times in
a row here before the lock cleared):

```bash
node /Users/junkawasaki/github/com-junkawasaki/scripts/resource-guard.mjs run build -- amu compile --target wasm32-browser app
```

```
shadow-cljs - config: .../worker/cljs/shadow-cljs.edn
shadow-cljs - starting via "clojure"
[:app] Compiling ...
[:app] Build completed. (111 files, 110 compiled, 0 warnings, 32.40s)
```

(SLF4J/Guava/`sun.misc.Unsafe` deprecation warnings from the JVM toolchain
omitted above — cosmetic, not build failures.)

Test build, same guard:

```bash
node /Users/junkawasaki/github/com-junkawasaki/scripts/resource-guard.mjs run build -- amu compile --target wasm32-browser test
```

```
[:test] Compiling ...
[:test] Build completed. (112 files, 111 compiled, 0 warnings, 22.43s)
```

Run the compiled tests with plain Node (no guard needed — this is fast and
local, not a shared-fleet build):

```bash
node out/tests.js
```

```
Testing arbitrage-worker.app-test
re-frame: Subscribe was called outside of a reactive context.
 https://day8.github.io/re-frame/FAQs/UseASubscriptionInAnEventHandler/
[... 17 more identical re-frame warning lines, one per direct rf/subscribe
     call made outside a Reagent render — expected and harmless for tests
     that read subs directly rather than through a mounted component ...]

Ran 6 tests containing 18 assertions.
0 failures, 0 errors.
```

Both builds pass genuinely (0 warnings, 0 failures, 0 errors) and this is
what was actually landed. `wrangler deploy` / `wrangler dev` were **not**
run — see [Where the code actually runs](../README.md#where-the-code-actually-runs)
in the README for why that remains unverified.

### §3-pre (historical, 2026-08-12, SvelteKit — this build no longer exists)

Kept verbatim for history. Every command below fails today with "no such
file or directory": `worker/svelte/` was deleted in the 2026-08-26 migration.

```bash
cd worker/svelte
npm install
```

```
added 92 packages, and audited 93 packages in 13s
...
npm warn allow-scripts 3 packages have install scripts not yet covered by allowScripts:
npm warn allow-scripts   esbuild@0.25.12 (postinstall: node install.js)
npm warn allow-scripts   esbuild@0.28.1 (postinstall: node install.js)
npm warn allow-scripts   workerd@1.20260804.1 (postinstall: node install.js)
```

**The blocked postinstall scripts do not break the build.** esbuild and workerd
ship their platform binaries as optional dependencies, and both the build (§3)
and the local run (§5) completed without approving anything. Left as-is
deliberately: approving install scripts is a supply-chain decision, not a
quickstart step.

This costs **268 MB** in `worker/svelte/node_modules`. Check you have the room
before starting; see §8.

```bash
npm run build
```

```
✓ built in 962ms        ← client
✓ built in 8.44s        ← server
> Using @sveltejs/adapter-cloudflare
  ✔ done
```

Typecheck, which is a script the repo already declares:

```bash
npm run check
```

```
COMPLETED 142 FILES 0 ERRORS 0 WARNINGS 0 FILES_WITH_PROBLEMS
```

Clean. Note what that number covers: 142 files rooted at `worker/svelte/`.
It does **not** cover `worker/src/app.ts`, which is the subject of §4.

## §4 Confirm which entry point ships (historical, pre-migration — see §3 for what's current)

`worker/wrangler.jsonc` sets `main` to the adapter output, so the build in §3 is
what Cloudflare would run:

```bash
cd ..    # back to worker/
ls -l svelte/.svelte-kit/cloudflare/_worker.js
```

```
-rw-r--r--  1 ...  4335 ... svelte/.svelte-kit/cloudflare/_worker.js
```

`worker/src/app.ts` is **not** in that build. Grep for two strings that appear
only in it:

```bash
grep -rl "edge-proxy+agentgateway-mcp+langserver" svelte/.svelte-kit || echo "not built"
grep -rl "mcp.etzhayyim.com" svelte/.svelte-kit
```

```
not built
svelte/.svelte-kit/output/server/entries/endpoints/xrpc/_...path_/_server.ts.js
```

So the upstream that ships is the MCP router from `+server.ts`, and
`src/app.ts`'s `dispatcher.etzhayyim.com` is dead code. It also does not
typecheck on its own — no `tsconfig.json` in this repo covers it:

```bash
find . -name "tsconfig*.json" -not -path "*/node_modules/*"
./svelte/node_modules/.bin/tsc --noEmit --target es2022 --module es2022 \
  --moduleResolution bundler --strict src/app.ts
```

```
./svelte/tsconfig.json
./svelte/.svelte-kit/tsconfig.json
src/app.ts(55,13): error TS2304: Cannot find name 'ExportedHandler'.
```

`ExportedHandler` comes from `@cloudflare/workers-types`, which is not a
dependency anywhere in the repo. **Do not delete `src/app.ts` on the strength of
this** — choosing between the two facades is a design decision. This step only
establishes that they disagree and that one of them is unreachable.

### One thing worth knowing before you deploy

`_worker.js` imports across its own directory boundary:

```js
import { Server } from "./../output/server/index.js";
import { manifest, prerendered, base_path } from "./../cloudflare-tmp/manifest.js";
```

The deployable unit is therefore the whole `.svelte-kit/` tree (768 KB), not the
140 KB `cloudflare/` directory. Copying `cloudflare/` somewhere on its own
produces a worker that cannot start.

## §5 Run it locally and probe every route (historical, pre-migration)

```bash
cd svelte
npm run preview -- --port 4321
```

**`vite preview` listens on IPv6 only.** Measured on this machine, against the
same running server:

```
curl http://127.0.0.1:4321/   →  curl: (7) Failed to connect ... after 0 ms
curl http://[::1]:4321/       →  200
curl http://localhost:4321/   →  200
```

Use `localhost` or `[::1]`. Reaching for `127.0.0.1` looks exactly like "the
server didn't start" and costs a few minutes every time.

From another shell:

```bash
curl -sS -o /dev/null -w '%{http_code} %{content_type}\n' http://localhost:4321/
curl -sS -w '\n%{http_code}\n' -X POST -H 'content-type: application/json' \
  -d '{}' http://localhost:4321/xrpc/com.etzhayyim.apps.arb.ping
curl -sS -o /dev/null -w '%{http_code}\n' -X OPTIONS http://localhost:4321/xrpc/x
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:4321/health
```

| request | result | reading |
|---|---|---|
| `GET /` | `200 text/html`, `<title>worker</title>` | the scaffold status page renders |
| `POST /xrpc/com.etzhayyim.apps.arb.ping` | `500 {"message":"Internal Error"}` | **expected today** — see below |
| `OPTIONS /xrpc/x` | `204` | CORS preflight is the only route that works without upstream |
| `GET /health` | `404` | confirms §4: `src/app.ts`'s `/health` is not deployed |

The 500 is not a local misconfiguration. The preview server logs the cause:

```
[500] POST /xrpc/com.etzhayyim.apps.arb.ping
TypeError: fetch failed
```

`+server.ts` calls the MCP router with a bare `await fetch(...)` and no
`try`/`catch`. When the host does not resolve (§6), the throw escapes the
handler and SvelteKit substitutes its generic 500 — so the route's own error
shapes (`400` for a missing NSID, `502` for an MCP-level error) are unreachable
while the router is down. **This is worth fixing, and fixing it is a code
change, not a documentation change.**

While you are here: `/` reports `Routes 0` and "No public route is declared",
but `wrangler.jsonc` declares two. The page is unedited scaffold output with
`routeCount: 0` hardcoded in `+page.svelte`; it is not reading the config.

## §6 The network reality (still true — the upstream network has not changed)

```bash
for h in etzhayyim.com arb.etzhayyim.com arb2x301.etzhayyim.com \
         mcp.etzhayyim.com dispatcher.etzhayyim.com; do
  printf '%-32s %s\n' "$h" "$(dig +short "$h" | head -1)"
done
```

```
etzhayyim.com                    172.67.179.128
arb.etzhayyim.com
arb2x301.etzhayyim.com
mcp.etzhayyim.com
dispatcher.etzhayyim.com
```

Only the parent zone resolves. Both declared routes, both upstreams, and the
`did:web` base for all 10 actor DIDs in `PROJECT.jsonld` are unresolved. **This
app has never been deployed**, and the service it proxies to does not exist at
the name it expects.

That ordering matters for anyone planning to ship this: standing up
`arb.etzhayyim.com` gets you a status page and a 500. The MCP router has to
exist first.

## §7 What this document has not done (as of the 2026-08-12 pre-migration build; §3 states what 2026-08-26 did and did not verify)

Recorded so nobody reads the sections above as broader than they are.

- **No deploy.** `wrangler deploy` was never run, and `wrangler` is not a
  dependency of this repo — §3 installs SvelteKit and the Cloudflare *adapter*,
  not the CLI. Deploying also needs a Cloudflare account with the
  `etzhayyim.com` zone, which is a credential question outside this file.
- **No `wrangler dev`.** §5 uses `vite preview`, which runs the SvelteKit server
  under Node, not under workerd. Bindings (`ASSETS`, `vars`,
  `DISPATCHER_INTERNAL_SECRET`) are therefore **not** exercised — in preview,
  `event.platform` is undefined and `+server.ts` silently falls through to its
  hardcoded `DEFAULT_MCP_ROUTER_URL`. Whether the `vars` in `wrangler.jsonc`
  arrive correctly under workerd is untested.
- **No successful XRPC round trip.** Every `POST /xrpc/…` observed here failed
  at DNS. The request shape the MCP router expects (`jsonrpc 2.0`,
  `tools/call`, `structuredContent` unwrapping) has never been confirmed
  against a live router from this repo.
- **No signal produced.** The BPMN contracts and the Python
  `kotodama.ingest.arbitrage` module that compute proposals were not extracted
  into this repo and were not run.
- **The NoExecution boundary was read, not tested.** It holds by absence of a
  broker client, not by an assertion. There was no test suite in this repo at
  all as of 2026-08-12. **This has partially changed**: as of 2026-08-26,
  `worker/cljs/test/arbitrage_worker/app_test.cljk` covers the status page's
  rendering logic (`cljs.test`, 6 tests / 18 assertions, see §3) — but it does
  not touch the NoExecution boundary, which still holds by absence, not by
  assertion.

## §8 Disk and cleanup

Pre-migration (SvelteKit), the build left three untracked, regenerable
directories, all now moot since `worker/svelte/` is gone:

| path | size |
|---|---|
| `worker/svelte/node_modules/` | 268 MB |
| `worker/svelte/.svelte-kit/` | 768 KB |
| `worker/svelte/.wrangler/` | small |

Post-migration (ClojureScript), `worker/cljs/` leaves its own untracked,
regenerable directories (measured 2026-08-26, after the §3 build):

| path | size |
|---|---|
| `worker/cljs/node_modules/` | 31 MB |
| `worker/cljs/.shadow-cljs/` | 51 MB |
| `worker/cljs/public/js/` | 12 MB (the built app bundle — regenerate with `npm run build`) |
| `worker/cljs/out/` | 52 KB (`node_modules/`, `.shadow-cljs/`, `public/js/`, `out/`, `.cpcache/` — all in `.gitignore`) |

To reclaim the space:

```bash
rm -rf worker/cljs/node_modules worker/cljs/.shadow-cljs worker/cljs/public/js worker/cljs/out worker/cljs/.cpcache
# pre-migration paths below no longer exist; kept for history
rm -rf worker/svelte/node_modules worker/svelte/.svelte-kit worker/svelte/.wrangler
```

`npm install` also writes **`package-lock.json`, which is neither committed nor
ignored** — so `git status` stays dirty after §3. That is deliberate: whether to
pin the lockfile is a dependency-policy decision for whoever owns this repo, and
silently ignoring the file would hide the choice. Commit it or ignore it on
purpose; do not let this document decide.
