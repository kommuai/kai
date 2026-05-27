# Kai main baseline (pre-refactor migration)

Captured: 2026-05-27

| Item | Value |
|------|--------|
| Branch | `main` @ `5bdc589` |
| Docker image | `kai-main-kai:latest` @ `f881ebc53b48` |
| Container | `kommu_chatbot` :6090 |
| Merge-base with `origin/refactor` | run `git merge-base HEAD origin/refactor` |

## API contract samples

See JSON files in this directory:

- `agent_message_hi.json` — normal reply
- `agent_message_la.json` — handover
- `agent_message_frozen.json` — frozen (empty message)
- `agent_message_resume.json` — resume
- `admin_refresh_sop.json` — knowledge refresh

## Rollback

Redeploy previous image and branch per `rollback.txt`:

```bash
cd /Users/kommu/Downloads/kai-main
git checkout main
docker compose build kai && docker compose up -d kai
```

Preserve `./data`, `./agent_workspace`, `./secrets`, `.env`.
