
let
  pkgs = import <nixpkgs> {};
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    flask flask-cors flask-bcrypt pyjwt pymongo python-dotenv
  ]);
in
pkgs.mkShell {
  packages = [ pythonEnv pkgs.git pkgs.mongodb-tools ];
  shellHook = ''
    echo "🔧 NajibSTL Flask shell ready (port 5000)"
    echo "Use: python backend.py"
  '';
}
