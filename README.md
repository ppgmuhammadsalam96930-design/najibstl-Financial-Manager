# NajibSTL - Financial Manager (Server-protected, local-friendly)

This package ensures your original HTML runs on your devices (localhost/file) without intrusive "please login" notices while still enforcing server-side auth for cloud features.

Files included:
- stl-original.local.html  (modified HTML with local-trust override; visually identical to your original)
- backend.py               (Flask backend that enforces allowed emails and serves /app only with JWT)
- .env                    (example filled with your Mongo URI placeholder and generated SECRET_KEY)
- requirements.txt
- docker-compose.yml
- README.md

How local-friendly behavior works:
- When you open the HTML on your own device (file:// or http://localhost), the script will detect trusted context and automatically allow UI to render without forcing login modal.
- Cloud sync/features that require JWT still require login via /auth/login; but the page won't constantly show the "please login" intrusive message on your devices.
- To access cloud features from other devices, users must login using the allowed emails and passwords you've provisioned.

Steps to run:
1. Extract this package and edit `.env` to replace `<db_password>` with your real MongoDB password.
2. For Atlas mode: `docker compose --profile atlas up --build` OR install requirements and run `python backend.py`.
3. For local mode: `docker compose --profile local up --build` (this will start a local MongoDB container).
4. Access app after login at: `http://localhost:5000/app` or open `stl-original.local.html` locally for UI-only testing.

Security notes:
- SECRET_KEY included is randomly generated; keep `.env` private.
- The local-trust override is convenience for your own devices only (it uses hostname/protocol checks + localStorage). It's not a replacement for server-side auth.
- For production, use HTTPS and set cookies secure=True.

Generated at: 2025-11-08T16:14:29.879875 UTC
