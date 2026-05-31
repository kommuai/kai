#!/usr/bin/env bash
# Install user systemd units for the full Kai stack (engine, Studio, WhatsApp).
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_UNIT_DIR="${HOME}/.config/systemd/user"
ENV_DIR="${HOME}/.config/kai"
STACK_ENV="${ENV_DIR}/kai-stack.env"
STACK_EXAMPLE="${SCRIPT_DIR}/kai-stack.env.example"
BRIDGE_ENV="${ENV_DIR}/whatsapp-bridge.env"
BRIDGE_EXAMPLE="${SCRIPT_DIR}/whatsapp-bridge.env.example"
KAI_REPO="${KAI_REPO:-${HOME}/workspace/kai}"
BRIDGE_DIR="${KAI_REPO}/studio/whatsapp-bridge"
FRONTEND_DIR="${KAI_REPO}/studio/frontend"

START_AFTER=0
STOP_MANUAL=0
for arg in "$@"; do
  case "$arg" in
    --start) START_AFTER=1 ;;
    --stop-manual) STOP_MANUAL=1 ;;
  esac
done

mkdir -p "${USER_UNIT_DIR}" "${ENV_DIR}"

install_unit() {
  local name="$1"
  sed "s|%h|${HOME}|g" "${SCRIPT_DIR}/${name}" > "${USER_UNIT_DIR}/${name}"
  echo "  installed ${name}"
}

echo "==> Installing systemd units"
for u in kai.target kai-engine.service kai-studio-api.service kai-studio-ui.service kai-whatsapp-bridge.service; do
  install_unit "${u}"
done

if [[ ! -f "${STACK_ENV}" ]]; then
  sed "s|%h|${HOME}|g" "${STACK_EXAMPLE}" > "${STACK_ENV}"
  echo "Created ${STACK_ENV}"
else
  echo "Keeping existing ${STACK_ENV}"
fi

if [[ ! -f "${BRIDGE_ENV}" ]]; then
  sed "s|%h|${HOME}|g" "${BRIDGE_EXAMPLE}" > "${BRIDGE_ENV}"
  echo "Created ${BRIDGE_ENV}"
else
  echo "Keeping existing ${BRIDGE_ENV}"
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
  echo "ERROR: Node.js 20+ required. Set NODE_BIN in ${STACK_ENV}." >&2
  exit 1
fi

KAI_PYTHON=""
for py in \
  "${HOME}/miniconda3/bin/python3" \
  "${HOME}/.pyenv/shims/python3" \
  "/usr/bin/python3"; do
  if [[ -x "${py}" ]] && PYTHONPATH="${KAI_REPO}" "${py}" -c "import kai" 2>/dev/null; then
    KAI_PYTHON="${py}"
    break
  fi
done
if [[ -z "${KAI_PYTHON}" ]]; then
  echo "ERROR: No Python with kai package. Set KAI_PYTHON in ${STACK_ENV}." >&2
  exit 1
fi

set_env_var() {
  local file="$1"
  local var="$2"
  local val="$3"
  if grep -q "^${var}=" "${file}" 2>/dev/null; then
    sed -i "s|^${var}=.*|${var}=${val}|" "${file}"
  else
    echo "${var}=${val}" >> "${file}"
  fi
}

for file in "${STACK_ENV}" "${BRIDGE_ENV}"; do
  set_env_var "${file}" "NODE_BIN" "${NODE_BIN}"
  set_env_var "${file}" "KAI_PYTHON" "${KAI_PYTHON}"
  set_env_var "${file}" "KAI_REPO" "${KAI_REPO}"
  set_env_var "${file}" "KAI_TENANTS_ROOT" "${KAI_TENANTS_ROOT:-${HOME}/workspace}"
done

echo "Using NODE_BIN=${NODE_BIN} ($(${NODE_BIN} -v))"
echo "Using KAI_PYTHON=${KAI_PYTHON} ($(${KAI_PYTHON} --version))"

echo "==> npm install (whatsapp-bridge)"
(cd "${BRIDGE_DIR}" && npm install)

echo "==> npm install (studio frontend)"
(cd "${FRONTEND_DIR}" && npm install)

systemctl --user daemon-reload

# Prefer single target over standalone bridge unit
systemctl --user disable kai-whatsapp-bridge.service 2>/dev/null || true
systemctl --user enable kai.target

if ! loginctl show-user "$(whoami)" -p Linger 2>/dev/null | grep -q 'Linger=yes'; then
  echo ""
  echo "WARNING: user lingering is off — services may not start at boot until you log in."
  echo "  sudo loginctl enable-linger $(whoami)"
fi

echo ""
echo "Enabled kai.target (starts on boot when lingering is on)"
echo "  systemctl --user start kai.target"
echo "  systemctl --user status kai.target"

free_port() {
  local port="$1"
  if ss -tln 2>/dev/null | grep -q ":${port} "; then
    echo "Freeing port ${port}…"
    fuser -k "${port}/tcp" 2>/dev/null || true
    sleep 1
  fi
}

if [[ "${STOP_MANUAL}" -eq 1 ]] || [[ "${START_AFTER}" -eq 1 ]]; then
  for p in 6090 8080 5173 18791; do
    free_port "${p}"
  done
fi

if [[ "${START_AFTER}" -eq 1 ]]; then
  systemctl --user start kai.target
  sleep 4
  systemctl --user --no-pager status kai.target || true
  echo ""
  echo "Health checks:"
  curl -sf http://127.0.0.1:6090/health 2>/dev/null && echo "  engine :6090 OK" || echo "  engine :6090 —"
  curl -sf http://127.0.0.1:8080/health 2>/dev/null && echo "  studio :8080 OK" || echo "  studio :8080 —"
  curl -sf -o /dev/null http://127.0.0.1:5173/ 2>/dev/null && echo "  ui     :5173 OK" || echo "  ui     :5173 —"
  curl -sf http://127.0.0.1:18791/health 2>/dev/null | head -c 80 && echo " … bridge OK" || echo "  bridge :18791 —"
fi
