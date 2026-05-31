# shadou.io — Shadou Studio production edge

This server is on a private LAN (`192.168.x.x`) with no inbound ports. **Cloudflare Tunnel** exposes `https://shadou.io` to a local nginx container on `127.0.0.1:8780`.

## Architecture

```
Browser → Cloudflare (TLS) → cloudflared → nginx:8780 → / → Vite build (static)
                                              └→ /auth, /tenants, … → Studio API :8080
```

## Quick setup

```bash
cd ~/workspace/shadou/studio/deploy/shadou
chmod +x setup.sh
./setup.sh
```

## Cloudflare (one-time)

1. In [Cloudflare Dashboard](https://dash.cloudflare.com) → **shadou.io** → DNS: remove conflicting A/AAAA records for `@` and `www` when using a tunnel.
2. On the server:

```bash
~/.local/bin/cloudflared tunnel login
~/.local/bin/cloudflared tunnel create shadou
~/.local/bin/cloudflared tunnel route dns shadou shadou.io
~/.local/bin/cloudflared tunnel route dns shadou www.shadou.io
cp ~/workspace/shadou/studio/deploy/shadou/cloudflared-config.yml.example ~/.config/cloudflared/shadou.yml
# Edit shadou.yml: set tunnel id + credentials-file path from ~/.cloudflared/*.json
systemctl --user enable --now cloudflared-shadou.service
```

3. SSL/TLS mode: **Full** (tunnel terminates at Cloudflare; origin is HTTP on localhost).

## Studio backend env

Add to `studio/backend/.env` (and restart API):

| Variable | Value |
|----------|--------|
| `FRONTEND_URL` | `https://shadou.io` |
| `CORS_EXTRA_ORIGINS` | `https://shadou.io,https://www.shadou.io` |
| `GOOGLE_REDIRECT_URI` | `https://shadou.io/auth/google/callback` |
| `FACEBOOK_REDIRECT_URI` | `https://shadou.io/auth/facebook/callback` |

Update the same redirect URIs in Google Cloud Console / Meta Developer apps.

## Commands

```bash
# Rebuild UI after frontend changes
cd ~/workspace/shadou/studio/frontend && npm run build
docker compose -f ~/workspace/shadou/studio/deploy/shadou/docker-compose.yml up -d --force-recreate

journalctl --user -u cloudflared-shadou -f
curl -s http://127.0.0.1:8780/health
```

## Optional: stop Vite dev UI on :5173

Production uses the static build via nginx. You can disable `shadou-studio-ui.service` to avoid confusion:

```bash
systemctl --user disable --now shadou-studio-ui.service
```
