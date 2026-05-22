# Login Plan for `Emhub.smartserva.com/app.php` (PHP, with Captcha)

## Goal

Automatically sign in once, persist the authenticated session (cookies), and reuse it for later requests.

Captchas are handled interactively: the automation pauses, prompts the user to solve/enter the captcha, then submits the login form. This avoids bypassing or defeating captcha.

## Assumptions we need to confirm

1. Where the login form lives (is `app.php` itself the login page, or does it redirect to a separate login endpoint?).
2. The POST target URL and form field `name` attributes:
   - username field name
   - password field name
   - captcha input field name
   - any CSRF/hidden token field names
3. Captcha delivery method:
   - captcha is an `<img>` with a retrievable `src`
   - captcha value is typed into a specific input `name`

## Step-by-step flow (what the PHP client will do)

### 1. Start a fresh session

- Create a cookie jar (file-based, e.g. `data/cookies.txt`) for `curl`/HTTP state.
- GET the login page URL.
- Follow redirects and keep cookies.

Output (debug-only, to local disk when needed):
- Save the login page HTML to `data/debug/login_page.html` so we can inspect field names/tokens if parsing fails.

### 2. Extract the login form

- Parse the login page HTML and locate the login form:
  - `<form method="POST" action="...">` (or `GET`)
  - collect all hidden inputs (CSRF tokens, session parameters)
  - record the `action` URL (resolve relative paths against the base URL)

### 3. Extract captcha prompt data (human-in-the-loop)

We will try to find the captcha widgets in the HTML using heuristics:

- Captcha image:
  - find an `<img>` likely related to captcha (id/src/alt contains `captcha`, `verify`, `code`, etc.)
- Captcha input field:
  - find an `<input>` likely related to captcha (name/id contains `captcha`, `code`, `verify`)

Then:

1. Download/save the captcha image to something like `data/captcha/captcha.jpg` (or capture an equivalent image artifact depending on HTML).
2. Pause execution and prompt:
   - “Enter captcha code: ” (read from STDIN)

### 4. Submit credentials + captcha

- Build the POST payload:
  - username
  - password
  - hidden token(s)
  - `captcha` input value from the user prompt
  - any other required fields the form contains
- POST to the extracted form `action`, with the same cookie jar.
- Follow redirects.

### 5. Verify login succeeded

Validation methods (pick what matches the site behavior):

- Check for a known “logged-in” marker in the response HTML (e.g. username shown, logout link, dashboard elements).
- Or confirm a redirect to a non-login page.
- Or attempt a subsequent authenticated endpoint and check it no longer redirects to the login page.

If validation fails:
- Save:
  - last response HTML to `data/debug/last_response.html`
  - current cookie jar to `data/debug/cookies_after_submit.txt`
- Return an error indicating whether it looks like:
  - wrong username/password
  - wrong/expired captcha
  - CSRF token mismatch

### 6. Persist the authenticated session

Once verified:

- Keep the cookie jar file on disk (`data/cookies.txt`).
- For later runs:
  - attempt to reuse cookies first (GET an authenticated “known page”)
  - if not logged in (redirect back to login), repeat the interactive captcha flow.

## Non-goals / safety constraints

- Do not attempt to bypass captcha (no automated captcha solving/detection evasion).
- Do not store credentials in the repository.
- Do not print credentials to logs/console.

## What I need from you to finalize field parsing

1. Confirm whether `https://Emhub.smartserva.com/app.php` shows the login form directly.
2. Provide (without sharing the actual password) the `name` attributes of:
   - username input
   - password input
   - captcha input
3. (Optional) Paste the login page HTML (or at least the `<form>` portion) so we can implement robust parsing.

## Interactive CLI behavior (proposed)

When implemented, the PHP script should:

1. Run: `php bin/login-interactive.php`
2. Show: captcha image path (and prompt for captcha code)
3. Print: “Login successful” or a clear failure reason
