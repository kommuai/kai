# Rollback procedure

1. Stop refactor container:
   ```bash
   docker compose -f docker-compose.kommu.yml down
   ```
2. Restore code:
   ```bash
   git checkout 5bdc5892068e52e8083c333769231cecab85b033
   ```
3. Start legacy stack:
   ```bash
   docker compose up -d --build
   ```
4. Verify:
   ```bash
   curl -s -X POST http://127.0.0.1:6090/agent/message \
     -H 'Content-Type: application/json' \
     -d '{"phone_number":"+60000000000","content":"hi"}'
   ```

Image ID before cutover: see `migration/baseline/rollback.txt`.
