{
  description = "STL UDHIS Financial Manager Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            nodejs_20
            nodePackages.nodemon
            python311
            python311Packages.pip
            go
          ];

          env = {
            # Environment variables if needed
          };

          shellHook = ''
            echo "STL UDHIS Financial Manager Development Environment"
          '';
        };
      }
    );
}
