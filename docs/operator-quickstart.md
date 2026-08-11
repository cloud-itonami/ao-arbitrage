# Operator quickstart — `cloud-itonami/arbitrage`

Every command below was run end to end on **2026-08-12** against commit
`412fa8a` on `main`, and the output shown is the output that came back. Where a
step failed, the failure is recorded rather than fixed — see §7 for the list of
things this document does **not** claim to have done.

Read [`../README.md`](../README.md) first if you have not: this repo has two
worker entry points and only one of them ships, which makes §4 the step people
skip and then get confused by.

- §1 and §2 need **nothing installed** — not even Node.
- §3–§6 need **Node + npm** and about 270 MB of disk.
- §7 is the honest list of untested ground.

Timings are from an M-series Mac with a warm npm cache. Treat them as an order
of magnitude, not a benchmark.

---

## §1 Read the repo without installing anything

There are 13 tracked files. You can hold the whole thing in your head.

```bash
git ls-files
```

```
PROJECT.jsonld
README.edn
migration.edn
worker/kotodama.jsonld
worker/src/app.ts
worker/svelte/package.json
worker/svelte/src/app.html
worker/svelte/src/routes/+page.svelte
worker/svelte/src/routes/xrpc/[...path]/+server.ts
worker/svelte/svelte.config.js
worker/svelte/tsconfig.json
worker/svelte/vite.config.ts
worker/wrangler.jsonc
```

The four files that carry all the meaning:

| file | what it decides |
|---|---|
| `worker/kotodama.jsonld` | the agent's identity, its KPIs, and the **NoExecution / EducationalOnly** boundary |
| `worker/wrangler.jsonc` | which hosts it answers on, and **which file actually deploys** |
| `worker/svelte/src/routes/xrpc/[...path]/+server.ts` | the only outbound call in the repo |
| `PROJECT.jsonld` | the 10 actor DIDs this project claims |

## §2 Check the extraction record — no dependencies

`migration.edn` records what was carried out of `etzhayyim/root`:
`:tracked-files 11 :bytes 15234`. The two metadata files added during
extraction (`README.edn`, `migration.edn`) are not part of that count, so the
claim is still checkable today:

```bash
git ls-files PROJECT.jsonld worker | wc -l
git ls-files PROJECT.jsonld worker | xargs wc -c | tail -1
```

```
      11
   15234 total
```

Both match `migration.edn` exactly. If either number moves, someone has edited
extracted content without updating the record — that is the only thing this
check is for.

> The paths are **selected**, not filtered. An earlier draft of this file
> excluded the two metadata files with `grep -v` instead, which was correct
> right up until this document was committed and the count silently became 15.
> Naming the extracted paths keeps the check valid no matter what
> repo-level files get added later.

## §3 Build the worker that actually deploys

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

## §4 Confirm which entry point ships

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

## §5 Run it locally and probe every route

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

## §6 The network reality

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

## §7 What this document has not done

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
  broker client, not by an assertion. There is no test suite in this repo at
  all.

## §8 Disk and cleanup

The build leaves three untracked, regenerable directories:

| path | size |
|---|---|
| `worker/svelte/node_modules/` | 268 MB |
| `worker/svelte/.svelte-kit/` | 768 KB |
| `worker/svelte/.wrangler/` | small |

All three are in `.gitignore`. To reclaim the space:

```bash
rm -rf worker/svelte/node_modules worker/svelte/.svelte-kit worker/svelte/.wrangler
```

`npm install` also writes **`package-lock.json`, which is neither committed nor
ignored** — so `git status` stays dirty after §3. That is deliberate: whether to
pin the lockfile is a dependency-policy decision for whoever owns this repo, and
silently ignoring the file would hide the choice. Commit it or ignore it on
purpose; do not let this document decide.
