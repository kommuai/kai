#!/usr/bin/env bash
# Shadou engine installer — per-user layout (Hermes-style)
set -euo pipefail

SHADOU_HOME="${SHADOU_HOME:-$HOME/.shadou}"
INSTALL_DIR="${SHADOU_INSTALL_DIR:-$HOME/.local/share/shadou}"
BIN_DIR="${SHADOU_BIN_DIR:-$HOME/.local/bin}"
REPO_URL="${SHADOU_REPO_URL:-}"

log() { printf '==> %s\n' "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

need_cmd git
need_cmd python3

PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
  echo "Python 3.11+ required" >&2
  exit 1
fi

if [ -n "$REPO_URL" ]; then
  log "Cloning Shadou engine into $INSTALL_DIR"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" pull --ff-only
  else
    git clone "$REPO_URL" "$INSTALL_DIR"
  fi
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  INSTALL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  log "Using existing checkout at $INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [ ! -d .venv ]; then
  log "Creating virtualenv"
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

log "Installing Python dependencies"
pip install -q --upgrade pip
pip install -q -r requirements.txt

mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/.venv/bin/python" "$BIN_DIR/shadou-python" 2>/dev/null || true
cat > "$BIN_DIR/shadou" <<EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR" && exec "$INSTALL_DIR/.venv/bin/python" -m shadou.cli "\$@"
EOF
chmod +x "$BIN_DIR/shadou"

export SHADOU_HOME
if [ ! -f "$SHADOU_HOME/workspace.yaml" ]; then
  log "Initializing SHADOU_HOME at $SHADOU_HOME"
  SHADOU_HOME="$SHADOU_HOME" python -m shadou.cli workspace init --home "$SHADOU_HOME" || true
fi

ENV_FILE="$SHADOU_HOME/.env"
if [ ! -f "$ENV_FILE" ] && [ -f "$INSTALL_DIR/.env.example" ]; then
  cp "$INSTALL_DIR/.env.example" "$ENV_FILE"
  log "Created $ENV_FILE from .env.example — add API keys"
fi

log "Install complete"
echo ""
echo "  export PATH=\"$BIN_DIR:\$PATH\""
echo "  export SHADOU_HOME=\"$SHADOU_HOME\""
echo "  shadou pack install /path/to/tenant-pack"
echo "  shadou doctor"
echo "  cd $INSTALL_DIR && docker compose up -d   # optional"
