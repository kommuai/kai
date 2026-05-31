#!/usr/bin/env bash
# Deploy Shadou Studio for https://shadou.io (nginx edge + optional Cloudflare Tunnel).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$ROOT/../../frontend"
SYSTEMD_USER="$ROOT/../systemd-user"
DOMAIN="${SHADOU_DOMAIN:-shadou.io}"
CF_BIN="${HOME}/.local/bin/cloudflared"
CF_CFG="${HOME}/.config/cloudflared/shadou.yml"

echo "==> Building Studio frontend (same-origin API via nginx)..."
cd "$FRONTEND"
if [[ ! -d node_modules ]]; then
  npm ci
fi
npm run build

echo "==> Starting nginx edge on 127.0.0.1:8780 (Docker)..."
cd "$ROOT"
docker compose up -d --remove-orphans

echo "==> Installing cloudflared (user local) if missing..."
mkdir -p "${HOME}/.local/bin"
if [[ ! -x "$CF_BIN" ]]; then
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64) CF_ARCH=amd64 ;;
    aarch64|arm64) CF_ARCH=arm64 ;;
    *) echo "Unsupported arch: $ARCH"; exit 1 ;;
  esac
  TMP="$(mktemp)"
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}" -o "$TMP"
  chmod +x "$TMP"
  mv "$TMP" "$CF_BIN"
  echo "Installed $CF_BIN"
fi

echo "==> Installing systemd user units..."
mkdir -p "${HOME}/.config/systemd/user"
cp "$SYSTEMD_USER/shadou-edge.service" "${HOME}/.config/systemd/user/"
cp "$SYSTEMD_USER/cloudflared-shadou.service" "${HOME}/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable shadou-edge.service

if curl -fsS "http://127.0.0.1:8780/health" >/dev/null 2>&1; then
  echo "OK: edge health via http://127.0.0.1:8780/health"
else
  echo "WARN: edge health check failed — is shadou-studio-api running on :8080?"
fi

if [[ ! -f "$CF_CFG" ]]; then
  echo ""
  echo "Cloudflare Tunnel not configured yet. One-time setup:"
  echo "  1. cloudflared tunnel login"
  echo "  2. cloudflared tunnel create shadou"
  echo "  3. cloudflared tunnel route dns shadou shadou.io"
  echo "  4. cloudflared tunnel route dns shadou www.shadou.io"
  echo "  5. Copy cloudflared-config.yml.example → $CF_CFG (set tunnel id + credentials path)"
  echo "  6. systemctl --user enable --now cloudflared-shadou.service"
  echo ""
  echo "In Cloudflare DNS, records should be CNAME → <tunnel-id>.cfargotunnel.com (proxied orange cloud)."
else
  systemctl --user enable cloudflared-shadou.service
  systemctl --user restart cloudflared-shadou.service || true
  echo "Tunnel service enabled (see: journalctl --user -u cloudflared-shadou -f)"
fi

echo ""
echo "Update Studio backend OAuth/CORS (studio/backend/.env):"
echo "  FRONTEND_URL=https://${DOMAIN}"
echo "  CORS_EXTRA_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}"
echo "  GOOGLE_REDIRECT_URI=https://${DOMAIN}/auth/google/callback"
echo "  FACEBOOK_REDIRECT_URI=https://${DOMAIN}/auth/facebook/callback"
echo "Then: systemctl --user restart shadou-studio-api.service"
echo ""
echo "Done. Local preview: http://127.0.0.1:8780"
