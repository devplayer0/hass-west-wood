# West Wood Club for Home Assistant

A [Home Assistant](https://www.home-assistant.io/) integration that exposes the
**live member count** of [West Wood Club](https://westwood.ie/) gyms as sensors.

The West Wood app is a white-label build of **PerfectGym Go**, so this integration
talks to PerfectGym's backend (`https://goapi2.perfectgym.com`). The API was
reverse-engineered from a capture of the app's traffic; see [`api.md`](api.md) for
the documented endpoints.

## Features

- One occupancy sensor per club, reporting the number of members currently checked
  in (`GET /v1/Clubs/WhoIsInCount`).
- All selected clubs are grouped under a single **West Wood Club** device.
- `measurement` state class, so Home Assistant records long-term statistics and
  history graphs per club.
- A single poll per update interval feeds every sensor.

## Getting a token

Authentication is a long-lived bearer token. Generate one with `get-token.py`
(stdlib only — needs no dependencies):

```bash
WESTWOOD_EMAIL=you@example.com WESTWOOD_PASSWORD=... python get-token.py
```

It prints the token to stdout (credentials can also be entered interactively).

## Installation

### NixOS (flake)

This repo's flake exposes the integration as a package and an overlay. Add it as a
flake input on your Home Assistant host, apply the overlay, and list it in
`customComponents`:

```nix
# flake inputs
inputs.hass-west-wood.url = "git+ssh://git@git.nul.ie/dev/hass-west-wood.git";

# NixOS module
{ pkgs, ... }:
{
  nixpkgs.overlays = [ inputs.hass-west-wood.overlays.default ];

  services.home-assistant = {
    enable = true;
    extraComponents = [ "default_config" ];
    customComponents = [ pkgs.home-assistant-custom-components.west_wood_club ];
  };
}
```

### Manual

Copy `custom_components/west_wood_club/` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

## Configuration

The integration is configured through the UI:

1. **Settings → Devices & Services → Add Integration → West Wood Club**.
2. Paste a bearer token (from `get-token.py`).
3. Select the clubs to create sensors for.

If the token is later rejected, Home Assistant starts a reauth flow to paste a
fresh one.

## Development

See [`AGENTS.md`](AGENTS.md) for the dev environment (Nix flake + nix-direnv),
code style, and working with the traffic capture.
