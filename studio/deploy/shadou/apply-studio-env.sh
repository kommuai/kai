#!/usr/bin/env bash
# Merge shadou.io public URLs into studio/backend/.env (does not print secrets).
set -euo pipefail
ENV_FILE="${1:-$HOME/workspace/shadou/studio/backend/.env}"
DOMAIN="${SHADOU_DOMAIN:-shadou.io}"
python3 - "$ENV_FILE" "$DOMAIN" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
domain = sys.argv[2].strip().rstrip("/")
base = f"https://{domain}"
updates = {
    "FRONTEND_URL": base,
    "CORS_EXTRA_ORIGINS": f"{base},https://www.{domain}",
    "GOOGLE_REDIRECT_URI": f"{base}/auth/google/callback",
    "FACEBOOK_REDIRECT_URI": f"{base}/auth/facebook/callback",
}
lines: list[str] = []
if path.is_file():
    lines = path.read_text(encoding="utf-8").splitlines()
out: dict[str, str] = {}
order: list[str] = []
for line in lines:
    if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
        order.append(line)
        continue
    k, _, v = line.partition("=")
    k = k.strip()
    out[k] = v
    if k not in order:
        order.append(k)
for k, v in updates.items():
    out[k] = v
    if k not in order:
        order.append(k)
rendered: list[str] = []
for item in order:
    if item in out:
        rendered.append(f"{item}={out[item]}")
    else:
        rendered.append(item)
path.write_text("\n".join(rendered) + "\n", encoding="utf-8")
print(f"Updated {path} for {base}")
PY
