---
name: awai-arb-tick
description: "Use when running the awai-arb cron arbitrage tick."
---

# awai-arb tick

1. Read last 24h of `~/.hermes/profiles/awai-arb/workspace/arb_ledger.jsonl` (1 tick = 1 JSON line). If the ledger is unreadable/empty AND the sandbox is degraded (see below), fall back to fresh live GET measurement via `web_extract` — never invent numbers; label evidence as live-measured with timestamp.
2. Endpoints: torihiki-node `/head` `/book` (devnet, collateral unbacked — paper only), x402.nexus `/stats` `/api/catalog`, murakumo `/v1/models`, Coinbase spot BTC-USD/USDC-USD.
3. Proposals: DRAFT them into `workspace/pending_proposals_<YYYY-MM-DD>.json` (`{"status":"PENDING_POST","proposals":[{id: "arb-<ts>-<slug>", kind: information|goods|procedural|social, evidence, proposal}]}`). Do not POST from the agent turn: the no-agent job `awai-arb-propose-post` (`scripts/arb_post.py`, every 30m) sends them to `https://ossekai.arb.etzhayyim.com/proposals` and confirms each by read-back (since 2026-09-24). Propose-only; no public posts, no @mentions (Council-gated).

## Pitfalls (2026-09-22 run)
- `execute_code` is BLOCKED in cron mode (unattended approval policy) — do not plan around it.
- Local shell sandbox can silently no-op: exit_code 0 with EMPTY output for every command, and `read_file` shows workspace files as 0 bytes. Verify with a probe write + `search_files` before trusting any local command. When degraded, web tools (web_extract/web_search) still work but cannot POST — proposals must be deferred and the run reported as failed, never silently skipped.
- `browser_exec` may fail with "no CDP endpoint" when the cloud browser provider is unavailable.
- skill_manage description must be ≤60 chars and YAML-safe (quote it if it contains a colon).
- No-POST-run protocol (2026-09-23): when shell is no-op AND browser CDP is down, the only remaining POST path is a delegate_task child with its own terminal — but the child's shell can also be no-op, so have the child run `echo SANITY_OK` first and bail on empty output. execute_code is hard-blocked in cron mode (approval policy). When no POST path exists: save the fully-drafted proposals to workspace/pending_proposals_<date>.json (exact id/kind/evidence/proposal payloads, ready to POST next tick), report the run as [CRON_FAILURE], never silently skip and never fabricate a POST.
