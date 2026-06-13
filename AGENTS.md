# AGENTS.md

## Purpose

Groundwork for a **Home Assistant integration for West Wood Club** (an Irish gym
chain). The West Wood app is a white-label build of **PerfectGym Go**, so the
integration targets PerfectGym's hosted backend at `https://goapi2.perfectgym.com`.

The repo holds the reverse-engineering capture, the API docs derived from it, a
token helper, and the Home Assistant custom component itself (see Integration).

## Layout

- `api.md` — documented PerfectGym endpoints (login, club list, live occupancy),
  secrets redacted. The source of truth for API behaviour; extend it as more
  endpoints are mapped.
- `get-token.py` — logs in and prints a bearer token to stdout (stdlib only).
- `custom_components/west_wood_club/` — the Home Assistant integration.
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

## Code style

Python uses **single-quoted strings** (`'...'`). Reformat with
`ruff format --config "format.quote-style='single'" <paths>` (ruff is available via
`nix run nixpkgs#ruff`). Docstrings stay triple-double-quoted (`"""`).

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

## Integration

`custom_components/west_wood_club/` is a UI-configured (config-flow) integration.

- **Auth model:** the user pastes a long-lived bearer token (from `get-token.py`);
  no credentials are stored. A rejected token (`WestWoodAuthError` → coordinator
  raises `ConfigEntryAuthFailed`) triggers HA's reauth flow to paste a fresh one.
- **One device, N sensors:** a single `DataUpdateCoordinator` polls
  `WhoIsInCount` once per interval for all clubs; one `SensorEntity` per selected
  club reads its `club_id` out of `coordinator.data`. All sensors share one
  device (`identifiers={(DOMAIN, entry.entry_id)}`) named "West Wood Club".
- **Config flow steps:** `user` and `reauth` are HA-fixed names (dispatched by the
  flow *source*); `clubs` and `reauth_confirm` are reached because a form was shown
  with that `step_id` (HA calls `async_step_<step_id>` on submit). Every step name
  must also have a matching key under `config.step` in `strings.json`.
- **Nix:** `flake.nix` exposes `packages.west_wood_club` (built with
  `buildHomeAssistantComponent`) and `overlays.default`, which adds it to
  `pkgs.home-assistant-custom-components`. On a NixOS host, apply the overlay and
  list it in `services.home-assistant.customComponents`; it must be built against
  the same Python as the host's `home-assistant`. Bump `version` in both
  `manifest.json` and the flake on code changes. The integration has **no**
  external `requirements`, so no extra Nix packaging is needed.

## Security

The capture and `token.txt` hold live credentials/tokens. Keep them gitignored,
and prefer the `WESTWOOD_EMAIL` / `WESTWOOD_PASSWORD` env vars (read by
`get-token.py`) over hardcoding credentials anywhere.
