
{
  description = "NajibSTL Financial Manager - Flask + MongoDB (Nix Edition)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          flask flask-cors flask-bcrypt pyjwt pymongo python-dotenv
        ]);
      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          name = "najibstl-backend";
          src = ./.;
          buildInputs = [ pythonEnv ];
          installPhase = ''
            mkdir -p $out
            cp -r . $out
          '';
        };

        devShells.default = pkgs.mkShell {
          packages = [ pythonEnv pkgs.git pkgs.mongodb-tools ];
          shellHook = ''
            echo "🔧 NajibSTL Flask DevShell ready"
            echo "Loaded Python environment with Flask, JWT, pymongo, dotenv"
          '';
        };

        apps.default = {
          type = "app";
          program = "${pythonEnv}/bin/python backend.py";
        };
      });
}
