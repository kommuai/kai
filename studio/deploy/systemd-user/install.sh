#!/usr/bin/env bash
# Install user systemd unit for Kai WhatsApp bridge + worker.
set -eu

UNIT_NAME=kai-whatsapp-bridge.service
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC="${SCRIPT_DIR}/${UNIT_NAME}"
USER_UNIT_DIR="${HOME}/.config/systemd/user"
ENV_DIR="${HOME}/.config/kai"
ENV_FILE="${ENV_DIR}/whatsapp-bridge.env"
ENV_EXAMPLE="${SCRIPT_DIR}/whatsapp-bridge.env.example"
BRIDGE_DIR="${HOME}/workspace/kai/studio/whatsapp-bridge"

START_AFTER=0
for arg in "$@"; do
  case "$arg" in
    --start) START_AFTER=1 ;;
  esac
done

mkdir -p "${USER_UNIT_DIR}" "${ENV_DIR}"

sed "s|%h|${HOME}|g" "${UNIT_SRC}" > "${USER_UNIT_DIR}/${UNIT_NAME}"

if [[ ! -f "${ENV_FILE}" ]]; then
  sed "s|%h|${HOME}|g" "${ENV_EXAMPLE}" > "${ENV_FILE}"
  echo "Created ${ENV_FILE} — review paths and API keys."
else
  echo "Keeping existing ${ENV_FILE}"
fi

if [[ ! -d "${BRIDGE_DIR}" ]]; then
  echo "ERROR: Bridge directory not found: ${BRIDGE_DIR}" >&2
  echo "Adjust paths in ${ENV_FILE} or clone Kai to ~/workspace/kai." >&2
  exit 1
fi

NODE_BIN=""
for candidate in \
  "${HOME}/.nvm/versions/node/"*/bin/node \
  "${HOME}/miniconda3/bin/node" \
  "/usr/local/bin/node" \
  "/usr/bin/node"; do
  if [[ -x "${candidate}" ]]; then
    ver="$("${candidate}" -v 2>/dev/null | sed 's/^v//')"
    major="${ver%%.*}"
    if [[ "${major}" -ge 20 ]]; then
      NODE_BIN="${candidate}"
      break
    fi
  fi
done
if [[ -z "${NODE_BIN}" ]]; then
  echo "ERROR: Node.js 20+ required for Baileys. Install via nvm or set NODE_BIN in ${ENV_FILE}." >&2
  exit 1
fi

KAI_REPO="${KAI_REPO:-${HOME}/workspace/kai}"
KAI_PYTHON=""
for py in \
  "${HOME}/miniconda3/bin/python3" \
  "${HOME}/.pyenv/shims/python3" \
  "/usr/bin/python3"; do
  if [[ -x "${py}" ]] && PYTHONPATH="${KAI_REPO:-${HOME}/workspace/kai}" "${py}" -c "import kai" 2>/dev/null; then
    KAI_PYTHON="${py}"
    break
  fi
done
if [[ -z "${KAI_PYTHON}" ]]; then
  echo "ERROR: No Python with kai package found. Set KAI_PYTHON in ${ENV_FILE}." >&2
  exit 1
fi

for var in "NODE_BIN=${NODE_BIN}" "KAI_PYTHON=${KAI_PYTHON}"; do
  key="${var%%=*}"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s|^${key}=.*|${var}|" "${ENV_FILE}"
  else
    echo "${var}" >> "${ENV_FILE}"
  fi
done
echo "Using NODE_BIN=${NODE_BIN} ($(${NODE_BIN} -v))"
echo "Using KAI_PYTHON=${KAI_PYTHON} ($(${KAI_PYTHON} --version))"

echo "==> npm install in whatsapp-bridge"
(cd "${BRIDGE_DIR}" && npm install)

systemctl --user daemon-reload
systemctl --user enable "${UNIT_NAME}"

if ! loginctl show-user "$(whoami)" -p Linger 2>/dev/null | grep -q 'yes'; then
  echo ""
  echo "Tip: enable user lingering so the bridge survives logout:"
  echo "  sudo loginctl enable-linger $(whoami)"
fi

echo ""
echo "Installed ${UNIT_NAME}"
echo "  systemctl --user start ${UNIT_NAME}"
echo "  systemctl --user status ${UNIT_NAME}"
echo "  journalctl --user -u ${UNIT_NAME} -f"
echo "  curl -s http://127.0.0.1:18791/health | python3 -m json.tool"

# Stop stray manual bridge on the same port so systemd can bind.
if ss -tln 2>/dev/null | grep -q ':18791 '; then
  echo "Stopping existing process on port 18791 (if any)…"
  fuser -k 18791/tcp 2>/dev/null || true
  sleep 1
fi

if [[ "${START_AFTER}" -eq 1 ]]; then
  systemctl --user start "${UNIT_NAME}"
  sleep 2
  systemctl --user --no-pager status "${UNIT_NAME}" || true
fi
