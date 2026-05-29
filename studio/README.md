# Kai Studio

Web admin for multi-tenant Kai configuration: auth, tenant workspaces, Monaco editor, inbox, contacts, and channel setup (e.g. WhatsApp Baileys).

Lives in the **Kai monorepo** at `studio/` (sibling to the Python engine package `kai/` and root `docker-compose.yml` for the runtime).

## Quick start (development)

```bash
# From repo root
./studio/start.sh
```

Or separately:

```bash
cd studio/backend && cp .env.example .env && pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

cd studio/frontend && npm install && npm run dev
```

- Frontend: http://localhost:5173  
- API: http://localhost:8080  

`KAI_REPO` defaults to the monorepo root (parent of `studio/`). Override in `backend/.env` if needed.

## WhatsApp bridge + message worker (production)

QR linking and **live inbound/outbound WhatsApp** use the Node service in `studio/whatsapp-bridge/` (includes the multi-tenant worker).

**User systemd (recommended on a server):**

```bash
cd studio/deploy/systemd-user
./install.sh
systemctl --user start kai-whatsapp-bridge.service
systemctl --user status kai-whatsapp-bridge.service
```

Config: `~/.config/kai/whatsapp-bridge.env` (created from `whatsapp-bridge.env.example`).

Studio UI shows **WhatsApp live** vs **linked only** on Dashboard, Configuration, and Inbox. API: `GET /tenants/whatsapp-worker` and per-tenant `GET /tenants/{id}/channels`.

Set `WHATSAPP_BRIDGE_URL=http://127.0.0.1:18791` in `studio/backend/.env` if the API runs in Docker but the bridge runs on the host.

## Docker (Studio only)

Does **not** start the Kai message engine — use the root compose for that.

```bash
cd studio
cp backend/.env.example backend/.env   # fill secrets
docker compose up -d --build
```

| Service | Default port | Role |
|---------|--------------|------|
| `studio-api` | 8080 | FastAPI backend |
| `studio-web` | 5173 | Built React UI (nginx) |

Environment (optional):

| Variable | Purpose |
|----------|---------|
| `STUDIO_API_PORT` | Host port for API |
| `STUDIO_WEB_PORT` | Host port for UI |
| `KAI_REPO_HOST` | Host path mounted as `/kai-engine` (default: repo root `..`) |
| `KAI_TENANTS_ROOT` | Host path for tenant workspaces (default: `~/workspace`) |
| `VITE_API_URL` | API URL baked into frontend build (default: `http://localhost:8080`) |

## Layout

```
studio/
  backend/          FastAPI, SQLite admin DB, Kai subprocess helpers
  frontend/         React + Vite + Tailwind
  docker-compose.yml
  Dockerfile.backend
  Dockerfile.frontend
  start.sh
```

## OAuth & env

See [docs/STUDIO.md](../docs/STUDIO.md) for Google/Facebook setup and the full environment table.
