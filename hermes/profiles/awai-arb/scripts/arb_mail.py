#!/usr/bin/env python3
# awai-arb email capability: send + receive via Resend API (mail.kotoba.cloud).
# send:   python3 arb_mail.py send <to> <subject> <body-file>      (propose-gated, see SOUL)
# recv:   python3 arb_mail.py recv [limit]
# Both directions are real API calls; nothing is fabricated. Errors print and exit 1.
import json, os, sys, urllib.request, urllib.error

KEY = os.environ.get("RESEND_API_KEY", "")
FROM = "awai-arb@mail.kotoba.cloud"
API = "https://api.resend.com"

def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + KEY, "User-Agent": "awai-arb/0.1",
        "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def main():
    if not KEY:
        print("ERROR\tRESEND_API_KEY not set (profile .env)"); return 1
    cmd = sys.argv[1] if len(sys.argv) > 1 else "recv"
    if cmd == "send":
        if len(sys.argv) < 5:
            print("usage: arb_mail.py send <to> <subject> <body-file>"); return 2
        to, subject, body_file = sys.argv[2], sys.argv[3], sys.argv[4]
        body = open(body_file).read()
        r = call("POST", "/emails", {"from": FROM, "to": [to], "subject": subject, "text": body})
        print("SENT\t" + r.get("id", "?")); return 0
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    inbox = call("GET", "/emails/receiving?limit=%d" % limit)
    for e in inbox.get("data", []):
        detail = call("GET", "/emails/receiving/" + e["id"])
        sender = detail.get("from", e.get("from", "?"))
        if isinstance(sender, dict): sender = sender.get("address", "?")
        print("FROM\t%s\tSUBJ\t%s\tID\t%s" % (sender, (detail.get("subject") or "")[:80], e["id"]))
        print("BODY\t" + (detail.get("text") or "")[:500].replace("\n", " | "))
    if not inbox.get("data"):
        print("INBOX\t0")
    return 0

sys.exit(main())
