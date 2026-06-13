# AGENTS.md

## Purpose

Groundwork for a **Home Assistant integration for West Wood Club** (an Irish gym
chain). The West Wood app is a white-label build of **PerfectGym Go**, so the
integration targets PerfectGym's hosted backend at `https://goapi2.perfectgym.com`.

The integration itself isn't written yet — the repo currently holds a
reverse-engineering capture, the API docs derived from it, and a login helper.

## Layout

- `api.md` — documented PerfectGym endpoints (login, club list, live occupancy),
  secrets redacted. The source of truth for API behaviour; extend it as more
  endpoints are mapped.
- `get-token.py` — logs in and prints a bearer token to stdout (stdlib only).
- `android-flows.mitm` — mitmproxy capture of the app's traffic. **Gitignored and
  untracked**: it contains real credentials and a bearer token in cleartext. Never
  commit it or copy its secrets into tracked files.
- `token.txt` — a captured/extracted bearer token. Also gitignored.
- `flake.nix` / `.envrc` — Nix dev shell (provides `mitmproxy`).

## Dev environment

Nix flake + nix-direnv. `direnv allow` (or `nix develop`) enters a shell with
`mitmproxy`. There is no `python3` on PATH outside the shell — run Python via
`nix develop --command python ...`.

Gotchas:
- Nix flakes only see **git-tracked** files. `git add` new files before
  `nix develop` / `nix flake lock`, or Nix errors with "not tracked by Git".
- `nix develop --command` may change cwd — use **absolute paths** when a script
  opens `android-flows.mitm`.

## Working with the capture

Read flows with the mitmproxy Python API:

```python
from mitmproxy.io import FlowReader
from mitmproxy.http import HTTPFlow

with open("/abs/path/android-flows.mitm", "rb") as f:
    for flow in FlowReader(f).stream():
        if isinstance(flow, HTTPFlow) and "perfectgym.com" in flow.request.host:
            ...  # flow.request / flow.response
```

When dumping flows, redact `Authorization` / `Cookie` headers and the login body
(email + password) before writing anything to a tracked file.

## API essentials

Full detail in `api.md`. Quick reference:

- Responses are wrapped `{ "data": ..., "errors": ... }`; `errors` is `null` on success.
- **Auth:** `POST /v1/Authorize/LogInWithEmail` (white-label ID goes in the body)
  → reuse the returned `bearer <token>` as the `Authorization` header. Token
  expiry is unconfirmed (`expireTime` was `null`).
- Authenticated endpoints need **only** the `Authorization` header — the `X-Go-*`
  headers and app `User-Agent` the app sends are not required (verified against
  the clubs endpoint).
- **Live occupancy:** `GET /v1/Clubs/WhoIsInCount` → `count` per `clubId` (the main
  sensor signal). `clubId` maps to `id` from `GET /v1/Clubs/Clubs`.

## Security

The capture and `token.txt` hold live credentials/tokens. Keep them gitignored,
and prefer the `WESTWOOD_EMAIL` / `WESTWOOD_PASSWORD` env vars (read by
`get-token.py`) over hardcoding credentials anywhere.
