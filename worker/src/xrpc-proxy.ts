// PRESERVED, NOT WIRED. Moved verbatim (bytes unchanged below the `---`
// marker) from worker/svelte/src/routes/xrpc/[...path]/+server.ts during the
// Svelte -> ClojureScript frontend migration (see docs/operator-quickstart.md
// and README.md "Where the code actually runs").
//
// This was a SvelteKit *server route* — the only outbound network call in
// this repo, proxying POST /xrpc/<nsid> to the MCP router at
// AGENTGATEWAY_MCP_ROUTER_URL / MCP_ROUTER_URL (default
// https://mcp.etzhayyim.com/xrpc/com.etzhayyim.mcp.message). It is real
// backend/edge logic, not frontend markup, so it is out of scope for a
// Svelte-frontend-to-cljs migration (worker/cljs is a shadow-cljs :browser
// build with no server-side target) and out of scope for "leave the Worker
// backend under worker/ alone" (that instruction was about
// worker/src/app.ts, a *different*, already-unwired facade with a different
// upstream — dispatcher.etzhayyim.com, not mcp.etzhayyim.com — and a
// different NSID convention; see README.md's "two worker entry points"
// section). Deleting this file's logic outright, rather than preserving it,
// would have silently thrown away the one piece of real integration code in
// the repo.
//
// It still imports SvelteKit types (`@sveltejs/kit`, `./$types`) and will not
// compile as-is now that worker/svelte/ is gone. It requires its own
// tsconfig.json and a decision about how (or whether) to wire it into a real
// Worker entry point — same open question this repo's README already
// records for worker/src/app.ts. That decision was explicitly out of scope
// here; this file is a preserved reference, not a working build target.
//
// wrangler.jsonc's `main` no longer points at a SvelteKit build (there is
// none to build); the Worker now serves worker/cljs/public as static assets
// only. This proxy route is therefore not live in the deployed Worker even
// as reference code — it was not live before this migration either (see
// docs/operator-quickstart.md §6: none of mcp.etzhayyim.com,
// arb.etzhayyim.com, or arb2x301.etzhayyim.com resolve).
// --- original content below, byte-for-byte -------------------------------
import { json, type RequestEvent } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const DEFAULT_MCP_ROUTER_URL = 'https://mcp.etzhayyim.com/xrpc/com.etzhayyim.mcp.message';
type Env = Record<string, unknown> & { AGENTGATEWAY_MCP_ROUTER_URL?: string; MCP_ROUTER_URL?: string };
function envOf(event: RequestEvent): Env { return ((event.platform as { env?: Env } | undefined)?.env ?? {}) as Env; }
function mcpRouterUrl(env: Env): string { const configured = typeof env.AGENTGATEWAY_MCP_ROUTER_URL === 'string' && env.AGENTGATEWAY_MCP_ROUTER_URL.trim() ? env.AGENTGATEWAY_MCP_ROUTER_URL : typeof env.MCP_ROUTER_URL === 'string' && env.MCP_ROUTER_URL.trim() ? env.MCP_ROUTER_URL : DEFAULT_MCP_ROUTER_URL; return configured.replace(/\/+$/, ''); }
function noStore(body: unknown, init: ResponseInit = {}): Response { const headers = new Headers(init.headers); headers.set('cache-control', 'no-store'); return json(body, { ...init, headers }); }
export const POST: RequestHandler = async (event) => { const nsid = event.params.path; if (!nsid) return noStore({ error: 'Missing XRPC method' }, { status: 400 }); const input = await event.request.json().catch(() => ({})); const headers = new Headers(event.request.headers); headers.delete('host'); headers.set('content-type', 'application/json'); headers.set('x-etzhayyim-bff', 'sveltekit-edge-bff'); headers.set('x-etzhayyim-xrpc-method', nsid); const upstream = await fetch(mcpRouterUrl(envOf(event)), { method: 'POST', headers, body: JSON.stringify({ jsonrpc: '2.0', id: crypto.randomUUID(), method: 'tools/call', params: { name: nsid, arguments: input } }) }); const upstreamText = await upstream.text(); let payload: unknown = upstreamText; try { payload = upstreamText ? JSON.parse(upstreamText) : null; } catch { /* Preserve text payload. */ } if (!upstream.ok) return noStore({ error: 'MCP router request failed', upstream: payload }, { status: upstream.status }); if (payload && typeof payload === 'object' && 'error' in payload) { const error = (payload as { error?: { message?: string } }).error; return noStore({ error: error?.message ?? 'MCP router returned an error', upstream: payload }, { status: 502 }); } const result = payload && typeof payload === 'object' && 'result' in payload ? (payload as { result?: unknown }).result : payload; const structured = result && typeof result === 'object' && 'structuredContent' in result ? (result as { structuredContent?: unknown }).structuredContent : result; return noStore(structured ?? {}); };
export const OPTIONS: RequestHandler = async () => new Response(null, { status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST,OPTIONS', 'access-control-allow-headers': 'content-type,authorization', 'access-control-max-age': '86400' } });
