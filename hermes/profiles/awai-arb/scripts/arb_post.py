#!/usr/bin/env python3
# awai-arb proposal poster: send drafted proposals to the ossekai intake.
# The agent tick drafts proposals into workspace/pending_proposals_*.json; this
# script is the only thing that POSTs them. A proposal counts as posted only when
# a read-back of the intake lists its id. The intake stores prop:<id> in Cloudflare
# KV, whose list lags a write (measured 2026-09-24: absent 1 s after a 200), so a
# POST answered {"ok":true,"key":"prop:<id>"} is marked "accepted" and never sent
# again, and becomes "confirmed" on the run whose read-back lists it. The intake
# does not validate the body (an {"id"} alone is accepted), so the shape is
# checked here before sending. Propose-only: the intake is the ossekai
# Council-gated queue, never a public post or a mention.
#
#   python3 arb_post.py [--dry-run]
#
# stdout: SCANNED/POSTED/ALREADY/FAILED lines. exit 0 all confirmed, 1 some
# failed, 3 intake unreachable (nothing could be answered).
import glob, json, os, sys, time, urllib.request, urllib.error

INTAKE = "https://ossekai.arb.etzhayyim.com/proposals"
UA = "awai-arb/0.1 (+https://itonami.cloud)"  # CF-fronted endpoints 403 on no-UA python
KINDS = {"information", "goods", "procedural", "social"}
WS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
DRY = "--dry-run" in sys.argv

def req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={
        "User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8", "replace") or "null")

def remote_ids():
    status, d = req("GET", INTAKE)
    items = (d or {}).get("items") or []
    if d.get("count") is not None and d["count"] != len(items):
        raise RuntimeError(f"intake listed {len(items)} of count {d['count']} (paged?)")
    return {((i.get("body") or {}).get("id")) for i in items}

def save(path, doc):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

try:
    have = remote_ids()
except Exception as e:
    print(f"REFUSE\tintake unreachable\t{e!r}")
    sys.exit(3)

files = sorted(glob.glob(os.path.join(WS, "pending_proposals_*.json")))
posted = already = failed = scanned = 0
for path in files:
    doc = json.load(open(path))
    if doc.get("status") != "PENDING_POST":
        continue
    changed = False
    for p in doc.get("proposals") or []:
        scanned += 1
        pid = p.get("id", "")
        if p.get("post_status") == "accepted" and pid not in have:
            print(f"PENDING-READBACK\t{pid}\taccepted, not yet listed")
            continue
        if p.get("post_status") == "confirmed" or pid in have:
            if p.get("post_status") != "confirmed":
                p["post_status"] = "confirmed"; p["posted_at"] = p.get("posted_at") or "before-this-run"; changed = True
            already += 1
            continue
        if not pid.startswith("arb-") or p.get("kind") not in KINDS or not p.get("evidence") or not p.get("proposal"):
            print(f"FAILED\t{pid or '?'}\tmalformed (needs arb- id, kind in {sorted(KINDS)}, evidence, proposal)")
            failed += 1
            continue
        if DRY:
            print(f"WOULD-POST\t{pid}\t{p['kind']}")
            continue
        try:
            status, resp = req("POST", INTAKE, {k: p[k] for k in ("id", "kind", "evidence", "proposal")})
        except urllib.error.HTTPError as e:
            print(f"FAILED\t{pid}\tHTTP {e.code} {e.read()[:200]!r}")
            failed += 1
            continue
        if (resp or {}).get("ok") is True and (resp or {}).get("key") == f"prop:{pid}":
            p["post_status"] = "accepted"
            p["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            changed = True
            posted += 1
            print(f"POSTED\t{pid}\tHTTP {status} {resp.get('key')}; confirmed on a later read-back")
        else:
            print(f"FAILED\t{pid}\tHTTP {status} unexpected answer {str(resp)[:200]}")
            failed += 1
    if not DRY and changed:
        if all(p.get("post_status") == "confirmed" for p in doc.get("proposals") or []):
            doc["status"] = "POSTED"
        save(path, doc)

print(f"SCANNED\t{scanned}")
print(f"POSTED\t{posted}\nALREADY\t{already}\nFAILED\t{failed}")
sys.exit(1 if failed else 0)
