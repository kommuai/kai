#!/usr/bin/env bash
# Kai engine installer — per-user layout (Hermes-style)
set -euo pipefail

KAI_HOME="${KAI_HOME:-$HOME/.kai}"
INSTALL_DIR="${KAI_INSTALL_DIR:-$HOME/.local/share/kai}"
BIN_DIR="${KAI_BIN_DIR:-$HOME/.local/bin}"
REPO_URL="${KAI_REPO_URL:-}"

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
  log "Cloning Kai engine into $INSTALL_DIR"
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
ln -sf "$INSTALL_DIR/.venv/bin/python" "$BIN_DIR/kai-python" 2>/dev/null || true
cat > "$BIN_DIR/kai" <<EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR" && exec "$INSTALL_DIR/.venv/bin/python" -m kai.cli "\$@"
EOF
chmod +x "$BIN_DIR/kai"

export KAI_HOME
if [ ! -f "$KAI_HOME/workspace.yaml" ]; then
  log "Initializing KAI_HOME at $KAI_HOME"
  KAI_HOME="$KAI_HOME" python -m kai.cli workspace init --home "$KAI_HOME" || true
fi

ENV_FILE="$KAI_HOME/.env"
if [ ! -f "$ENV_FILE" ] && [ -f "$INSTALL_DIR/.env.example" ]; then
  cp "$INSTALL_DIR/.env.example" "$ENV_FILE"
  log "Created $ENV_FILE from .env.example — add API keys"
fi

log "Install complete"
echo ""
echo "  export PATH=\"$BIN_DIR:\$PATH\""
echo "  export KAI_HOME=\"$KAI_HOME\""
echo "  kai pack install /path/to/tenant-pack"
echo "  kai doctor"
echo "  cd $INSTALL_DIR && docker compose up -d   # optional"
