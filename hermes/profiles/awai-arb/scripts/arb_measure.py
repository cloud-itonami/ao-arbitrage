#!/usr/bin/env python3
# awai-arb measurement tick: probe arbitrage surfaces, append findings to ledger.
# Real probes only - values come from live HTTP responses, never computed placeholders.
import json, os, time, urllib.request, sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "arb_ledger.jsonl")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

UA = "awai-arb/0.1 (+https://itonami.cloud)"  # CF-fronted endpoints 403 on no-UA python

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def num(x, default=None):
    try: return float(x)
    except (TypeError, ValueError): return default

surfaces_scanned = 0
findings = []

# --- surface 1: torihiki-node devnet order book / head ---
try:
    head = get("https://torihiki-node.04-feasts-minded.workers.dev/head")
    book = get("https://torihiki-node.04-feasts-minded.workers.dev/book")
    surfaces_scanned += 1
    findings.append({"kind": "internal_book", "surface": "torihiki-devnet", "head": head if isinstance(head, (str, int, float)) else "ok", "book": book if len(str(book)) < 2000 else "large"})
except Exception as e:
    findings.append({"kind": "probe_error", "surface": "torihiki-devnet", "error": repr(e)})

# --- surface 2: external reference spots (ground truth) ---
refs = {}
for name, url, key in [
    ("BTC-USD", "https://api.coinbase.com/v2/prices/BTC-USD/spot", "amount"),
    ("USDC-USD", "https://api.coinbase.com/v2/prices/USDC-USD/spot", "amount"),
]:
    try:
        d = get(url)
        v = num(d["data"][key])
        refs[name] = v
        surfaces_scanned += 1
    except Exception as e:
        findings.append({"kind": "probe_error", "surface": name, "error": repr(e)})

# --- surface 3: x402.nexus catalog + stats (pay-per-call goods/service pricing) ---
try:
    cat = get("https://x402.nexus/api/catalog")
    items = cat if isinstance(cat, list) else cat.get("items") or cat.get("catalog") or []
    surfaces_scanned += 1
    findings.append({"kind": "x402_catalog", "surface": "x402.nexus", "item_count": len(items) if hasattr(items, "__len__") else "unknown"})
except Exception as e:
    try:
        cat = get("https://x402.nexus/catalog")
        surfaces_scanned += 1
        findings.append({"kind": "x402_catalog", "surface": "x402.nexus", "raw_head": str(cat)[:400]})
    except Exception as e2:
        findings.append({"kind": "probe_error", "surface": "x402.nexus/catalog", "error": repr(e2)})

try:
    stats = get("https://x402.nexus/stats")
    surfaces_scanned += 1
    findings.append({"kind": "x402_stats", "surface": "x402.nexus", "stats": stats if len(str(stats)) < 1500 else "large"})
except Exception as e:
    findings.append({"kind": "probe_error", "surface": "x402.nexus/stats", "error": repr(e)})

# --- surface 4: murakumo model pricing (inference cost plane) ---
try:
    models = get("https://api.murakumo.cloud/v1/models")
    priced = []
    for m in (models.get("data") or []):
        p = m.get("pricing") or {}
        if p: priced.append({"id": m.get("id"), "pricing": p})
    surfaces_scanned += 1
    findings.append({"kind": "murakumo_pricing", "surface": "api.murakumo.cloud", "priced_models": priced})
except Exception as e:
    findings.append({"kind": "probe_error", "surface": "murakumo", "error": repr(e)})

tick = {
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "refs": refs,
    "surfaces_scanned": surfaces_scanned,
    "findings": findings,
}
with open(OUT, "a") as f:
    f.write(json.dumps(tick, ensure_ascii=False) + "\n")

# evidence-floor style output: distinguish scanned vs errored
errs = sum(1 for x in findings if x.get("kind") == "probe_error")
print(f"SCANNED\t{surfaces_scanned}")
print(f"ERRORS\t{errs}")
print(f"LEDGER\t{OUT}")
sys.exit(0 if surfaces_scanned > 0 else 3)  # 3 = nothing scanned, not success
