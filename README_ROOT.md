# NajibSTL Financial Manager — Fullstack Package (Nix + Docker + Python)

Generated: 2025-11-08T16:32:02.653174 UTC

This package includes everything you need to run the app locally (development) or in Docker.
Files included:
- stl-original.local.html  (frontend optimized for local trust)
- backend.py               (Flask backend; enforces allowed emails and JWT)
- .env                     (example config with MONGO_URI placeholder)
- .env.example             (same as .env but with <DB_PASSWORD_HERE> placeholder)
- requirements.txt
- docker-compose.yml       (profiles: atlas, local)
- flake.nix                (Nix flake to develop/run the backend)
- shell.nix                (Nix shell for non-flake environments)
- README.md                (detailed usage; included as stl_final_with_env/README.md)

## Quick start (Atlas)
1. Edit `.env` and replace `<DB_PASSWORD_HERE>` with your MongoDB Atlas password.
2. Run with Docker Compose (Atlas profile):
   ```bash
   docker compose --profile atlas up --build
   ```
   or
   ```bash
   pip install -r requirements.txt
   python backend.py
   ```

## Quick start (Local MongoDB Docker)
1. Update `.env` to use local Mongo URI if needed or use the provided docker-compose local profile.
2. Run:
   ```bash
   docker compose --profile local up --build
   ```

## Nix (developer)
- With flakes enabled (recommended):
  ```bash
  nix develop
  nix run .
  ```
  The flake will set up a Python environment and `nix run .` will execute `python backend.py` (port 5000). `.env` variables will be read by the backend using python-dotenv.
- With classic nix-shell:
  ```bash
  nix-shell
  python backend.py
  ```

**Security reminder:** keep `.env` private and do not commit real credentials to public repos.

