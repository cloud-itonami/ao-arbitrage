// arb.etzhayyim.com thin edge facade (ADR-2604282300).
//
// Business logic lives in BPMN + Python LangServer:
//   - BPMN: etzhayyim-root/00-contracts/bpmn/com/etzhayyim/arb
//   - Python: kotodama.ingest.arbitrage

interface SecretBinding {
  get(): Promise<string>;
}

interface Env {
  DISPATCHER_URL?: string;
  DISPATCHER_INTERNAL_SECRET?: string | SecretBinding;
  APP_NANOID?: string;
  APP_DISPLAY_NAME?: string;
}

const OWNER_DID = "did:web:arb.etzhayyim.com";
const NSID_PREFIX = "com.etzhayyim.apps.arb.";

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    if (url.pathname === "/health" || url.pathname === "/_app/meta") {
      return json({
        ok: true,
        actor: OWNER_DID,
        nanoid: env.APP_NANOID ?? "arb2x301",
        displayName: env.APP_DISPLAY_NAME ?? "Arb - Cross-Asset Arbitrage Signals",
        execution: "edge-proxy+agentgateway-mcp+langserver",
        businessLogic: "40-engine/kotoba/crates/kotoba-kotodama/py/src/kotodama/ingest/arbitrage.py",
        bpmn: "etzhayyim-root/00-contracts/bpmn/com/etzhayyim/arb",
        adr: "ADR-0036, ADR-2604282300",
      });
    }

    const nsid = url.pathname.startsWith("/xrpc/") ? url.pathname.slice("/xrpc/".length) : "";
    if (req.method === "POST" && nsid.startsWith(NSID_PREFIX)) {
      let body: Record<string, unknown> = {};
      try {
        const text = await req.text();
        body = text ? JSON.parse(text) : {};
      } catch (e) {
        return json({ ok: false, error: `invalid JSON body: ${e instanceof Error ? e.message : String(e)}` }, 400);
      }
      for (const [key, value] of url.searchParams) {
        if (!(key in body)) body[key] = value;
      }
      return proxyToDispatcher(env, nsid, body);
    }

    return new Response("Not Found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;

async function proxyToDispatcher(env: Env, nsid: string, body: Record<string, unknown>): Promise<Response> {
  const base = (env.DISPATCHER_URL ?? "https://dispatcher.etzhayyim.com").replace(/\/+$/, "");
  const headers: Record<string, string> = { "content-type": "application/json" };
  const trust = await internalTrustSecret(env);
  if (trust) headers["x-internal-trust"] = trust;

  const resp = await fetch(`${base}/xrpc/${nsid}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const text = await resp.text();
  return new Response(text, {
    status: resp.status,
    headers: {
      "content-type": resp.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}

async function internalTrustSecret(env: Env): Promise<string> {
  const binding = env.DISPATCHER_INTERNAL_SECRET;
  if (!binding) return "";
  try {
    return typeof binding === "string" ? binding : await binding.get();
  } catch {
    return "";
  }
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}
