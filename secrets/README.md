# Google service account (warranty sheets)

Kai reads warranty data from Google Sheets when credentials are valid.

1. Create a Google Cloud service account with **Spreadsheets read** access.
2. Download the JSON key and save it here as:

   `google_service_account.json`

3. Share the warranty spreadsheet with the service account email (`client_email` in the JSON).

4. In `.env`, set:

   ```bash
   GOOGLE_SHEETS_CREDENTIALS_JSON=./secrets/google_service_account.json
   GOOGLE_SHEETS_WARRANTY_SHEET_ID=<spreadsheet id>
   GOOGLE_SHEETS_WARRANTY_GID=<tab gid>
   ```

Docker Compose mounts this folder at `/app/secrets` (read-only).

This directory is gitignored; do not commit key files.
