# Kai Studio (monorepo)

Kai Studio is the operator UI for tenant workspaces. It ships inside the Kai repository under **`studio/`**, separate from the message **engine** image and `docker-compose.yml` at the repo root.

## Two stacks

| Stack | Command | Purpose |
|-------|---------|---------|
| **Engine** | `docker compose up -d --build` (repo root) | WhatsApp/agent runtime, `KAI_HOME` volume |
| **Studio** | `cd studio && docker compose up -d --build` | Admin UI API + static frontend |

They share no container. Studio calls the engine via subprocess (`kai compile`, `kai_reply`, `kai_inbound`) using `KAI_REPO` pointing at the monorepo root.

## Paths

| Variable | Default (dev) | Description |
|----------|---------------|-------------|
| `KAI_REPO` | Monorepo root (`kai/` clone) | Engine source for compile & inbox tools |
| `KAI_TENANTS_ROOT` | `~/workspace` | Where `kai-tenant-*` dirs are created |
| `FRONTEND_URL` | `http://localhost:5173` | CORS + OAuth redirects |

## Google OAuth

1. [Google Cloud Console](https://console.cloud.google.com/) → Credentials → OAuth 2.0 Client ID (Web).
2. Redirect URI: `http://localhost:8080/auth/google/callback`
3. Set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in `studio/backend/.env`.

## Facebook OAuth

1. [Meta for Developers](https://developers.facebook.com/) → Facebook Login.
2. Redirect URI: `http://localhost:8080/auth/facebook/callback`
3. Set `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` in `studio/backend/.env`.

Production requires HTTPS callback URLs.

## Tenant workspace layout

When a tenant is created in Studio:

```
${KAI_TENANTS_ROOT}/kai-tenant-<slug>/
  workspace.yaml
  system_prompt.md
  knowledge/master_faq.md
  compiled/
  data/
  tools/plugins/
```

## Backend layout

```
studio/backend/
  main.py
  kai_paths.py          # monorepo-aware KAI_REPO default
  kai_reply.py
  kai_inbound.py
  routers/
```
