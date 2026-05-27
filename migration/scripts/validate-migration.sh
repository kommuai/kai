#!/usr/bin/env bash
# Compare production (6090) vs staging refactor (6091) API contracts.
set -euo pipefail
PROD="${KAI_PROD_URL:-http://127.0.0.1:6090}"
STAGE="${KAI_STAGE_URL:-http://127.0.0.1:6091}"
ADMIN="${ADMIN_TOKEN:-changeme-strong}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/validation"
mkdir -p "$OUT"

check() {
  local name="$1" url="$2" payload="$3"
  curl -s -X POST "$url/agent/message" -H 'Content-Type: application/json' -d "$payload" > "$OUT/${name}.json"
  python3 -c "
import json,sys
d=json.load(open('$OUT/${name}.json'))
for k in ('type','message','next_state'):
    assert k in d, f'missing {k} in $name: {d}'
print('$name', d.get('type'), d.get('next_state'), 'ok')
"
}

check hi_prod "$PROD" '{"phone_number":"+60000001001","content":"hi"}'
check hi_stage "$STAGE" '{"phone_number":"+60000001002","content":"hi"}'
check la_stage "$STAGE" '{"phone_number":"+60000001003","content":"LA"}'
check frozen_stage "$STAGE" '{"phone_number":"+60000001003","content":"hi"}'
check resume_stage "$STAGE" '{"phone_number":"+60000001003","content":"resume"}'

curl -s -X POST "$STAGE/admin/refresh-sop" -H "X-Admin-Token: $ADMIN" > "$OUT/stage_refresh.json"
python3 -c "import json; d=json.load(open('$OUT/stage_refresh.json')); assert d.get('ok'), d"

echo "Validation artifacts in $OUT"
