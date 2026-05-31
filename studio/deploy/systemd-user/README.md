# Shadou stack — user systemd (autostart on login / boot)

Starts the full Shadou dev stack after reboot (requires **user lingering**).

| Service | Port | Role |
|---------|------|------|
| `shadou-engine` | 6090 | Support runtime API |
| `shadou-studio-api` | 8080 | Studio backend |
| `shadou-studio-ui` | 5173 | Studio frontend (Vite) |
| `shadou-whatsapp-bridge` | 18791 | WhatsApp + worker (+ STT :18792) |

## Install

```bash
cd ~/workspace/shadou/studio/deploy/systemd-user
./install.sh --start
```

This copies units to `~/.config/systemd/user/`, creates `~/.config/shadou/shadou-stack.env`, runs `npm install` for bridge + frontend, and enables **`shadou.target`**.

## Boot without login

User services only run at boot if lingering is on:

```bash
loginctl show-user "$(whoami)" -p Linger   # should be yes
sudo loginctl enable-linger "$(whoami)"    # if needed
```

## Commands

```bash
systemctl --user start shadou.target      # start all
systemctl --user stop shadou.target       # stop all
systemctl --user status shadou.target
systemctl --user restart shadou-studio-api.service
journalctl --user -u shadou-engine -f
```

## Env files

| File | Used by |
|------|---------|
| `~/.config/shadou/shadou-stack.env` | Engine, Studio API/UI |
| `~/.config/shadou/whatsapp-bridge.env` | WhatsApp bridge |
| `~/workspace/shadou/studio/backend/.env` | Studio API (OAuth, JWT, etc.) |

Do not commit secrets. `install.sh` auto-fills `SHADOU_PYTHON` and `NODE_BIN`.
