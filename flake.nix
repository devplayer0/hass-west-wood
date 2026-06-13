{
  description = "Home Assistant integration for West Wood gyms (PerfectGym API)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # Adds the integration to pkgs.home-assistant-custom-components so it can be
      # used directly in services.home-assistant.customComponents.
      overlay = final: prev: {
        home-assistant-custom-components = prev.home-assistant-custom-components // {
          west_wood_club = final.buildHomeAssistantComponent {
            owner = "deplayer0";
            domain = "west_wood_club";
            version = "0.1.0";
            src = ./.;
          };
        };
      };
    in
    {
      overlays.default = overlay;
    }
    // flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system}.extend overlay;
      in
      {
        packages = rec {
          west_wood_club = pkgs.home-assistant-custom-components.west_wood_club;
          default = west_wood_club;
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            mitmproxy
          ];
        };
      });
}
