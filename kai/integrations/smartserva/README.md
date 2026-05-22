# smartserva

Automation for creating SMARTSERVA visitor passes on:

`https://emhub.smartserva.com/app.php`

## Production CLI

Use the tool:

- `create_visitor_pass.py`

It performs:

1. Login with captcha OCR retry.
2. Delivery visitor creation (`Visitors -> New Visitor -> Delivery` equivalent backend flow).
3. Random Malaysian name generation.
4. Random Malaysian mobile number generation.
5. Visitor pass link retrieval.

## Setup

Install dependencies:

`python3 -m pip install --user requests ddddocr`

Set credentials (do not hardcode):

- `SMARTSERVA_USERNAME`
- `SMARTSERVA_PASSWORD`

Example:

`export SMARTSERVA_USERNAME='your_email@example.com'`

`export SMARTSERVA_PASSWORD='your_password'`

## Usage

Call with just date and time:

`python3 create_visitor_pass.py --date 2026-03-28 --time 18:30`

Optional:

- `--unit-id 383` to target a specific unit id.
- `--max-login-attempts 12` to tune captcha retries.
- `--timeout 30` to tune request timeout.

## Output

The command prints JSON with:

- random visitor name
- random Malaysian mobile
- visitor id/status
- final visitor pass link

## Notes

- Date format: `YYYY-MM-DD`
- Time format: `HH:MM` (24-hour)
