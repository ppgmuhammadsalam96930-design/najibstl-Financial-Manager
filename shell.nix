{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
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
}
