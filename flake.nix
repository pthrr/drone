{
  description = "Drone project dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nixgl = {
      url = "github:nix-community/nixGL";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, nixgl }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        nixGLIntel = nixgl.packages.${system}.nixGLIntel;
        openscad-wrapped = pkgs.writeShellScriptBin "openscad" ''
          exec ${pkgs.lib.getExe nixGLIntel} ${pkgs.lib.getExe pkgs.openscad} "$@"
        '';
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.go-task
            openscad-wrapped
            pkgs.uv
            pkgs.libiio
            pkgs.kas
            pkgs.qdl
            pkgs.android-tools
            pkgs.mtools
            pkgs.picocom
          ];
          env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.libiio ];
        };
      });
}
