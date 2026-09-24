# hermes/ — the resident bots this repository runs as

This directory is the **source of truth** for the Hermes profiles that act on
behalf of this repository. A profile lives here, not in `~/.hermes/profiles/`:
the host directory is materialized from this tree and checked against it.

```
hermes/profiles/<profile>/
  SOUL.md          the bot's standing instructions
  profile.yaml     one-line description
  config.yaml      model / provider routing (host-local keys removed)
  cron/jobs.json   job definitions only — no run state
  skills/<name>/   skills this bot owns (the generic bundled skills are not copied)
  scripts/         scripts its cron jobs run
```

**Never here:** `.env` and any secret value, the measurement ledger and
`workspace/`, sessions, memories, logs, caches, run state. Secrets are placed
on the host from kagi (ADR-2607198200); run data stays on the host.

Materialize / check from the superproject:

```
kbb --backend sci scripts/hermes-profile-repo.cljk materialize <repo-path> [<profile>]
kbb --backend sci scripts/hermes-profile-repo.cljk check       <repo-path> [<profile>]
```

`check` exits 0 when the host matches, 1 on drift (named per file), 2 when it
could not compare. Edits the bot makes to its own SOUL or skills on the host
show up as drift and are brought back with `export`, then committed here.

## Profiles

| profile | what it does | cron |
|---|---|---|
| `awai-arb` | measures arbitrage surfaces (torihiki devnet, x402.nexus, murakumo pricing, Coinbase refs) into an append-only ledger, and proposes findings to the ossekai intake. Propose-only; never trades. | `awai-arb-measure` every 30m (script), `awai-arb-ossekai-report` every 6h (agent) |
