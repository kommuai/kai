# Kai WhatsApp Bridge (Baileys)

Sidecar for **QR linking** (Studio onboarding) and **multi-tenant message worker** (inbound → Kai → WhatsApp reply).

## Run locally

```bash
cd studio/whatsapp-bridge
npm install
export KAI_TENANTS_ROOT=/home/ting/workspace   # parent of kai-tenant-* dirs
export KAI_REPO=/home/ting/workspace/kai
npm start
```

Listens on `http://127.0.0.1:18791` by default (`WHATSAPP_BRIDGE_PORT`).

Studio backend uses `WHATSAPP_BRIDGE_URL` (default `http://127.0.0.1:18791`).

**Note:** Do not use port 8091 on this machine — it is often taken by nginx/Cursor bridge.

## What runs in one process

| Component | Role |
|-----------|------|
| HTTP API (`/v1/link/*`) | QR pairing during new-tenant wizard |
| HTTP API (`POST /v1/worker/send`) | Studio human-agent replies → WhatsApp DM |
| Worker manager | Scans `KAI_TENANTS_ROOT` every 15s for `whatsapp_baileys` tenants |

When a new tenant is created (or `workspace.yaml` / auth creds change), the worker **starts automatically** on the next scan — no manual restart.

During QR linking, the worker **pauses** that tenant’s auth directory so only the link socket is active.

## Tenant requirements

Under `kai-tenant-<slug>/`:

- `workspace.yaml` → `channels.inbound.provider: whatsapp_baileys` and `channels.whatsapp_baileys.enabled: true`
- `data/whatsapp/baileys-auth/creds.json` (from Studio QR flow)

## Environment

| Variable | Default |
|----------|---------|
| `KAI_TENANTS_ROOT` | `~/workspace` |
| `KAI_REPO` | `studio/whatsapp-bridge/../..` |
| `KAI_PYTHON` | `python3` |
| `WHATSAPP_BRIDGE_PORT` | `18791` |
| `WHATSAPP_WORKER_SCAN_MS` | `15000` |
| `WHATSAPP_WORKER_ENABLED` | `1` (set `0` to disable worker, link API only) |

## Health

`GET /health` → `{ ok: true, worker: { tenants: [...], ... } }`

## Inbound path

WhatsApp message → `kai_inbound.py` (`KAI_HOME` = tenant workspace) → `support_runtime` → reply sent via Baileys. Sessions appear in Studio **Inbox** (`data/sessions.db`).

## systemd (Phase B)

```bash
cd ../deploy/systemd-user && ./install.sh
systemctl --user enable --now kai-whatsapp-bridge.service
```

See `studio/README.md` for Studio UI status badges.
