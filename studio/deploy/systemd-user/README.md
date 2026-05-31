# Kai stack — user systemd (autostart on login / boot)

Starts the full Kai dev stack after reboot (requires **user lingering**).

| Service | Port | Role |
|---------|------|------|
| `kai-engine` | 6090 | Support runtime API |
| `kai-studio-api` | 8080 | Studio backend |
| `kai-studio-ui` | 5173 | Studio frontend (Vite) |
| `kai-whatsapp-bridge` | 18791 | WhatsApp + worker (+ STT :18792) |

## Install

```bash
cd ~/workspace/kai/studio/deploy/systemd-user
./install.sh --start
```

This copies units to `~/.config/systemd/user/`, creates `~/.config/kai/kai-stack.env`, runs `npm install` for bridge + frontend, and enables **`kai.target`**.

## Boot without login

User services only run at boot if lingering is on:

```bash
loginctl show-user "$(whoami)" -p Linger   # should be yes
sudo loginctl enable-linger "$(whoami)"    # if needed
```

## Commands

```bash
systemctl --user start kai.target      # start all
systemctl --user stop kai.target       # stop all
systemctl --user status kai.target
systemctl --user restart kai-studio-api.service
journalctl --user -u kai-engine -f
```

## Env files

| File | Used by |
|------|---------|
| `~/.config/kai/kai-stack.env` | Engine, Studio API/UI |
| `~/.config/kai/whatsapp-bridge.env` | WhatsApp bridge |
| `~/workspace/kai/studio/backend/.env` | Studio API (OAuth, JWT, etc.) |

Do not commit secrets. `install.sh` auto-fills `KAI_PYTHON` and `NODE_BIN`.
