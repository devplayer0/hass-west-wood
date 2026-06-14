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
  Its `brand/` dir holds the integration icon/logo, extracted from the capture's
  `westwoodclub-ie.png` asset.
- `android-flows.mitm` — mitmproxy capture of the app's traffic. **Gitignored and
  untracked**: it contains real credentials and a bearer token in cleartext. Never
  commit it or copy its secrets into tracked files.
- `token.txt` — a captured/extracted bearer token. Also gitignored.
- `flake.nix` / `.envrc` — Nix dev shell (provides `mitmproxy`).

## Dev environment

Nix flake + nix-direnv. `direnv allow` enters a shell with `mitmproxy`/`python`.

To run Python/mitmproxy from a non-interactive shell (where direnv does **not**
auto-activate and there's no `python` on PATH), use `direnv exec .`:

```
direnv exec . python script.py
```

This reuses nix-direnv's **cached** dev shell (~0.06s). Prefer it over
`nix develop --command ...`, which re-evaluates the flake every call (slow, and
noisy with "Git tree is dirty" warnings).

Gotchas:
- Nix flakes only see **git-tracked** files. `git add` new files before
  `nix develop` / `nix flake lock`, or Nix errors with "not tracked by Git".
- Use **absolute paths** when a script opens `android-flows.mitm` — `nix develop
  --command` resets cwd to the repo root (`direnv exec .` keeps the current dir).

## Code style

Python uses **single-quoted strings** (`'...'`). Reformat with
`ruff format --config "format.quote-style='single'" <paths>` (ruff is available via
`nix run nixpkgs#ruff`). Docstrings stay triple-double-quoted (`"""`).

In prose (commit messages, docs, comments), backtick-quote anything code-like —
paths, filenames, identifiers, commands, endpoints, HTTP headers, field/JSON
keys, UUIDs/IDs, env vars — rather than plain or double-quoted text. If in doubt
and it's a literal token from code or an API, backtick it.

## Working with the capture

Read flows with the mitmproxy Python API:

```python
from mitmproxy.io import FlowReader
from mitmproxy.http import HTTPFlow

with open('/abs/path/android-flows.mitm', 'rb') as f:
    for flow in FlowReader(f).stream():
        if isinstance(flow, HTTPFlow) and 'perfectgym.com' in flow.request.host:
            ...  # flow.request / flow.response
```

When dumping flows, redact `Authorization` / `Cookie` headers and the login body
(email + password) before writing anything to a tracked file.

Some questions the capture can't answer (token lifecycle, the white-label ID,
error codes) need the app itself. If you're pointed at **decompiled APK output**
(e.g. apktool `smali/`), grep it there — but it's R8-obfuscated: class names are
mangled and library types (e.g. OkHttp, `androidx.security.crypto`) may be
shrunk/repackaged, so a missing grep hit is not proof of absence. No such
decompilation lives in this repo (the user can supply a local apktool dump on
request; app package `com.perfectgym.perfectgymgo2.westwoodclub`). The original
ELPassion source package names survive obfuscation under
`smali/com/elpassion/perfectgym/`, which is the useful entry point.

### How the app stores the bearer token

Confirmed from the decompilation (relevant because it answers the token-lifecycle
question and shows there's no second auth secret to capture):

- The login response DTO (`AccountAuthorizationGoApiDto`) carries `token`,
  `tokenType`, `authorizationHeader`, and a **nullable `expireTime`**.
  `DtoMapperKt.asAuthorizeResponse` keeps **only the bare `token`** string;
  `tokenType`/`authorizationHeader`/`expireTime` are discarded. The app
  reconstructs `Authorization: bearer <token>` itself per request.
- The token is **persisted in `EncryptedSharedPreferences`** (androidx
  security-crypto, R8-repackaged to `l3.*`; AES-256-GCM master key in the Android
  Keystore). The store class is `f6/o` (interface `f6/p`); the backing file is
  named `wevgebvre` and values are Moshi-JSON-encoded. Token key: **`"token"`**
  (writer `f6/o.h(String)`, reader `f6/o.r()`).
- **Load path:** at DI-graph construction the provider (`androidx/room/v0`) calls
  `f6/p.r()` and passes the stored token into the `appmodel/s0` AppModel
  constructor as its initial value, which seeds the reactive `tokenS`
  (`Optional<String>`) stream — so the app comes up already authenticated.
  Login writes the new token back via `f6/p.h(...)` (dispatcher `z4/c`).
- **Legacy + migration:** older builds kept the same `"token"` key in the
  *plaintext* default `SharedPreferences` (`f6/b0`, via
  `PreferenceManager.getDefaultSharedPreferences`). `PerfectGymApplication` runs a
  one-time migration gated by an `isMigrated` flag: copy from `f6/b0` into the
  encrypted `f6/o`, then `clear()` + `deleteSharedPreferences()` the plaintext
  file. So the token is no longer recoverable in cleartext on current installs.

## API essentials

Full detail in `api.md`. Quick reference:

- Responses are wrapped `{ "data": ..., "errors": ... }`; `errors` is `null` on success.
- **Auth:** `POST /v1/Authorize/LogInWithEmail` (white-label ID goes in the body)
  → reuse the returned `bearer <token>` as the `Authorization` header. Treat the
  token as long-lived: there's no refresh token, the app persists only the token
  (not the email/password) and discards the response's `expireTime`, so refetch
  reactively on `401`/`403`. See `api.md` and the token-storage notes above.
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

## Checks

There is no test suite. Verify changes with:

- `direnv exec . python -m py_compile custom_components/west_wood_club/*.py` — fast
  syntax check of the component.
- `nix build .#west_wood_club` — builds the component and runs nixpkgs' manifest
  and import checks (the closest thing to CI here). Remember to `git add` new files
  first, or the flake won't see them.

## Security

The capture and `token.txt` hold live credentials/tokens. Keep them gitignored,
and prefer the `WESTWOOD_EMAIL` / `WESTWOOD_PASSWORD` env vars (read by
`get-token.py`) over hardcoding credentials anywhere.
