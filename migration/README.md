# Kai refactor migration (Kommu)

## Branches

- **Pre-migration baseline:** `main` @ `5bdc589` (see `migration/baseline/rollback.txt`)
- **Target:** `origin/refactor` merged into `main` with Kommu compatibility overlays

## Run production (after cutover)

```bash
cd /Users/kommu/Downloads/kai-main
docker compose -f docker-compose.kommu.yml up -d --build
```

Uses:

- Port **6090** → `kommu_chatbot`
- `~/.kai` (or mounted tenant pack) as `KAI_HOME` — FAQ, `workspace.yaml`, plugins
- `./secrets`, repo `.env` unchanged
- Prepare tenant home: `bash migration/scripts/prepare-kai-home.sh ~/.kai /path/to/kai-tenant-kommu`

## Staging (side-by-side)

```bash
docker compose -f docker-compose.staging.yml up -d --build
# http://127.0.0.1:6091
bash migration/scripts/validate-migration.sh
```

## Rollback

```bash
git checkout main
git reset --hard 5bdc5892068e52e8083c333769231cecab85b033  # or: git checkout migration/baseline/rollback.txt
docker compose up -d --build   # legacy docker-compose.yml
```

Do **not** delete `./data` or your `KAI_HOME` tenant pack (`~/.kai`).

## Rollback triggers

- n8n 5xx / missing `type` or `message` in `/agent/message` responses
- Widespread no-reply (`frozen` without user LA)
- `POST /admin/refresh-sop` fails
- Session DB path change (empty history for all users)
