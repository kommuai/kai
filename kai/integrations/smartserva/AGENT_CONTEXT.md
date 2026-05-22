# smartserva — agent context

Session log for this repo. Global handoff: `/home/ting/system-notes/AGENT_CONTEXT.md`.

## 2026-03-27 — Initial scaffold for PHP login automation (captcha-aware)

- Intent: create project `workspace/smartserva` to implement an automated login system in PHP for:
  - `https://Emhub.smartserva.com/app.php`
- Approach chosen for captcha: human-in-the-loop pause where the script prompts the user to enter the captcha code; automation reuses authenticated cookies after success.
- Files added:
  - `workspace/smartserva/README.md`
  - `workspace/smartserva/LOGIN_PLAN.md`
- Validation run:
  - `ls -la /home/ting/workspace/smartserva`

## Next actions

- Inspect the login page HTML to confirm form field `name` attributes (username/password/captcha) and CSRF hidden tokens.
- Implement the PHP client with a cookie jar and interactive captcha prompt.

## 2026-03-27 — Live execution check against emhub login

- Intent: user asked to run checks end-to-end and attempt successful captcha + login.
- Findings from live endpoint:
  - Login form fields confirmed: `username`, `password`, `capt`, hidden `action=login`, hidden `p=`.
  - Captcha image endpoint confirmed: `/capt.php?t=...`.
  - Actual login API path confirmed from frontend JS (`script_app.js`): `POST /process{p}.php` with `p=''` => `POST /process.php`, plus `ax=2`, `app=2`, `appt='u'`.
- Validation commands/outcomes:
  - `python requests` check with incorrect captcha produced JSON: `{"s":0,"msg":"Wrong Security Code",...}`.
  - Installed OCR dependency: `python3 -m pip install --user ddddocr` (success).
  - Automated retry run (OCR captcha + live login submissions) repeatedly returned: `{"s":0,"msg":"Wrong username or password",...}` for many attempts, indicating captcha passed but credentials were rejected.
  - Run ended after repeated attempts with a transient remote disconnect (`RemoteDisconnected`) likely due rate-limit/protection.
- Known risks/deferred:
  - Further retries may trigger temporary server-side protections.
  - Need updated/verified credentials or account status check before retrying.
- Next recommended action:
  - Confirm current valid credentials for `support@kommu.ai` (or reset password), then rerun a low-attempt login check.

## 2026-03-27 — Live login success with updated credentials

- Intent: rerun end-to-end login check with updated username/password provided by user.
- Validation command: Python session with OCR captcha solve + `POST /process.php` payload (`action=login`, `ax=2`, `app=2`, `appt='u'`).
- Outcome:
  - Attempt `1` returned JSON success signal: `s=2` (message empty).
  - This confirms captcha+login flow succeeded at API level for the provided credentials.
- Notes:
  - Follow-up page HTML check was inconclusive for a simple marker because the app shell still contains login markup.
  - Primary success criterion is backend login response `s=2`.

## 2026-03-27 — Visitor delivery creation + link retrieval (completed)

- Intent: execute user flow for `Visitors -> New Visitor -> Delivery`, submit a random visitor with phone number `1`, set `Valid From`, and retrieve the resulting visitor link.
- Execution method:
  - Verified UI path and form fields (`nm`, `tel`, `sh`, `action=add_vi`) via browser automation.
  - Stabilized submission by calling backend endpoints directly with authenticated session:
    - `POST /process2.php` `action=add_vi` (multipart form payload)
    - `POST /process3.php` `action=get_vi` to locate the created row id
    - `POST /process2.php` `action=get_vi_dt` to read `qr_link`
- Result:
  - Created visitor name: `Visitor0DT9Z`
  - Visitor id: `215842`
  - Status in registrations: `Approved`
  - Retrieved link: `https://emhub.smartserva.com/visitor_pass.php?v=03278MC9QK7SDE94YS4Z7XZ6RSGR4U`
- Validation outcomes:
  - Login response: `s=2`
  - Add visitor response: `{"s":2,"msg":"Added","action":"add_vi",...}`
  - Detail response: `{"s":2, ... "qr_link":"https://emhub.smartserva.com/visitor_pass.php?..."}`

## 2026-03-27 — Production automation CLI (date+time input)

- Intent: user requested a production automation tool callable with only visit date/time that auto-generates random Malaysian name and number, submits delivery visitor, and returns pass link.
- Files changed:
  - Added `workspace/smartserva/create_visitor_pass.py`:
    - args: `--date YYYY-MM-DD`, `--time HH:MM`, optional `--unit-id`
    - env creds: `SMARTSERVA_USERNAME`, `SMARTSERVA_PASSWORD`
    - OCR captcha login retries (`ddddocr`)
    - random Malaysian name + mobile generation
    - backend-equivalent visitor creation (`add_vi`) and pass-link retrieval (`get_vi_dt`)
    - JSON output for automation use
  - Updated `workspace/smartserva/README.md` with setup and usage.
- Validation run:
  - `python3 -m py_compile create_visitor_pass.py`
  - `python3 create_visitor_pass.py --help`
  - Live run: `SMARTSERVA_USERNAME=... SMARTSERVA_PASSWORD=... python3 create_visitor_pass.py --date 2026-03-28 --time 18:30`
  - Live result: success JSON with created visitor id and pass link (`ok: true`).
- Next actions:
  - Optionally add a scheduler wrapper (cron/systemd timer) if recurring auto-creation is needed.

## 2026-03-27 — Booking window-safe default time for omitted `--time`

- Intent: prevent runtime failures when caller omits time and current local time is outside SmartServa booking window.
- File changed:
  - `workspace/smartserva/create_visitor_pass.py`
    - `parse_schedule()` now selects a safe default when time is omitted:
      - if current hour >= 22: use next day `10:00`
      - if current hour < 6: use today `10:00`
      - else: keep current time
- Validation outcome:
  - End-to-end runtime call from Kai (`create_visitor_pass` via `support_runtime_service.execute`) now succeeds with `ok=True` and returns `visitor_pass_link` when no time is provided.
