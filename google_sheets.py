import os, io, csv, requests, re, json, base64
from urllib.parse import parse_qs, urlparse

# Primary warranty sheet
WARRANTY_CSV_URL = os.getenv("WARRANTY_CSV_URL", "")
# Secondary warranty sheet
EXTRA_WARRANTY_CSV_URL = os.getenv("EXTRA_WARRANTY_CSV_URL", "")
GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
GOOGLE_SHEETS_WARRANTY_SHEET_ID = os.getenv("GOOGLE_SHEETS_WARRANTY_SHEET_ID", "")
GOOGLE_SHEETS_WARRANTY_GID = os.getenv("GOOGLE_SHEETS_WARRANTY_GID", "")
GOOGLE_SHEETS_WARRANTY_EXTRA_GID = os.getenv("GOOGLE_SHEETS_WARRANTY_EXTRA_GID", "")

# In-memory stores
WARRANTY_DB = {}         
WARRANTY_BY_DONGLE = {}  

def _fetch_csv_rows(url: str):
    if not url:
        return []
    r = requests.get(url, timeout=20, headers={"User-Agent":"Kai/Sheets/1.0"})
    r.raise_for_status()
    content = r.content.decode("utf-8", errors="ignore")
    return list(csv.DictReader(io.StringIO(content)))


def _extract_sheet_id_and_gid_from_url(url: str) -> tuple[str, str]:
    if not url:
        return "", ""
    sid = ""
    gid = ""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if m:
        sid = m.group(1)
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    gid = (q.get("gid") or [""])[0]
    if not gid and "#" in url:
        frag = url.split("#", 1)[1]
        if frag.startswith("gid="):
            gid = frag.split("=", 1)[1]
    return sid, gid


def _gid_to_title(service, spreadsheet_id: str, gid: str) -> str:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sh in meta.get("sheets", []):
        props = sh.get("properties", {})
        if str(props.get("sheetId", "")) == str(gid):
            return props.get("title", "")
    return ""


def _fetch_sheet_rows_api(spreadsheet_id: str, gid: str) -> list[dict]:
    if not spreadsheet_id or not gid or not GOOGLE_SHEETS_CREDENTIALS_JSON:
        return []
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:  # noqa: BLE001
        print(f"[WARRANTY] Sheets API libs missing: {exc}")
        return []
    try:
        info = _load_service_account_info()
        if not info:
            print("[WARRANTY] GOOGLE_SHEETS_CREDENTIALS_JSON missing/invalid")
            return []
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        title = _gid_to_title(service, spreadsheet_id, gid)
        if not title:
            print(f"[WARRANTY] gid {gid} not found in sheet metadata")
            return []
        # Read full tab; Sheets trims to used range.
        values = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{title}!A:ZZ")
            .execute()
            .get("values", [])
        )
        if not values:
            return []
        header = values[0]
        rows = []
        for raw in values[1:]:
            row = {header[i]: (raw[i] if i < len(raw) else "") for i in range(len(header))}
            rows.append(row)
        return rows
    except Exception as exc:  # noqa: BLE001
        print(f"[WARRANTY] Sheets API fetch failed: {exc}")
        return []


def _load_service_account_info() -> dict:
    raw = (GOOGLE_SHEETS_CREDENTIALS_JSON or "").strip()
    if not raw:
        return {}
    # 1) direct JSON string
    if raw.startswith("{"):
        return json.loads(raw)
    # 2) file path in env var
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8") as fh:
            return json.load(fh)
    # 3) base64-encoded JSON
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception:  # noqa: BLE001
        return {}

def _norm_key(s: str) -> str:
    if not s: return ""
    s = str(s).strip()
    return "".join(ch for ch in s if ch.isdigit() or ch == '+')

def _norm_dongle(s: str) -> str:
    if not s: return ""
    return "".join(ch for ch in str(s).upper() if ch.isalnum())

def _norm_header(s: str) -> str:
    """Normalize header keys: strip, lower, collapse spaces, remove NBSP/zero-width, strip punctuation around."""
    if s is None: return ""
    s = str(s)
   
    s = s.replace("\u200b", "").replace("\u200c", "").replace("\ufeff", "").replace("\xa0", " ")
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
   
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"[^\w ]+", "", s)  # keep letters/digits/space
    return s

def _extract_field(row: dict, *candidates):
    """Return first non-empty value among candidate column names (case-insensitive, header-normalized)."""
    if not row:
        return ""
    low = {_norm_header(k): v for k, v in row.items()}
    for name in candidates:
        if name is None: 
            continue
        key = _norm_header(name)
        v = low.get(key)
        if v not in (None, ""):
            return v
    return ""

def _merge_rows_into_indexes(rows, source_tag=""):
    """Insert rows into WARRANTY_DB and WARRANTY_BY_DONGLE."""
    added_dongles = 0
    for r in rows:
        # phone-ish
        phone_like  = [
            _extract_field(r, "phone"), _extract_field(r, "mobile"),
            _extract_field(r, "whatsapp"), _extract_field(r, "contact")
        ]
        serial_like = [
            _extract_field(r, "serial"), _extract_field(r, "serial no"),
            _extract_field(r, "serial_no"), _extract_field(r, "device serial")
        ]
        # DONGLE ID variants — include headers with leading
        dongle_like = [
            _extract_field(r, "dongle id"), _extract_field(r, "dongle  id"),
            _extract_field(r, "dongle_id"), _extract_field(r, "dongle"),
            _extract_field(r, "device id"), _extract_field(r, "device_id"),
            _extract_field(r, "dongle id ")  
        ]

        # index phone/serial
        for k in phone_like + serial_like:
            k2 = _norm_key(k)
            if k2:
                WARRANTY_DB[k2] = r

        # index dongle id
        for d in dongle_like:
            d2 = _norm_dongle(d)
            if d2:
                WARRANTY_BY_DONGLE[d2] = r
                added_dongles += 1
    print(f"[WARRANTY] {source_tag} mapped {added_dongles} dongle ids.")

def fetch_warranty_all():
    """Load/merge warranty rows from both sheets."""
    global WARRANTY_DB, WARRANTY_BY_DONGLE
    WARRANTY_DB = {}
    WARRANTY_BY_DONGLE = {}

    total_rows = 0

    # API-first for private sheets, CSV fallback.
    primary_sid = GOOGLE_SHEETS_WARRANTY_SHEET_ID
    primary_gid = GOOGLE_SHEETS_WARRANTY_GID
    extra_gid = GOOGLE_SHEETS_WARRANTY_EXTRA_GID
    if not primary_sid and WARRANTY_CSV_URL:
        sid, gid = _extract_sheet_id_and_gid_from_url(WARRANTY_CSV_URL)
        primary_sid = sid
        if not primary_gid:
            primary_gid = gid
    if not primary_sid and EXTRA_WARRANTY_CSV_URL:
        sid, gid = _extract_sheet_id_and_gid_from_url(EXTRA_WARRANTY_CSV_URL)
        primary_sid = sid
        if not extra_gid:
            extra_gid = gid

    primary_rows = []
    if GOOGLE_SHEETS_CREDENTIALS_JSON and primary_sid and primary_gid:
        primary_rows = _fetch_sheet_rows_api(primary_sid, primary_gid)

    if primary_rows:
        print(f"[WARRANTY] Primary rows (Sheets API): {len(primary_rows)}")
        _merge_rows_into_indexes(primary_rows, source_tag="primary")
        total_rows += len(primary_rows)
    elif WARRANTY_CSV_URL:
        try:
            rows = _fetch_csv_rows(WARRANTY_CSV_URL)
            print(f"[WARRANTY] Primary rows: {len(rows)}")
            _merge_rows_into_indexes(rows, source_tag="primary")
            total_rows += len(rows)
        except Exception as e:
            print(f"[WARRANTY] Primary fetch failed: {e}")

    extra_rows = []
    if GOOGLE_SHEETS_CREDENTIALS_JSON and primary_sid and extra_gid:
        extra_rows = _fetch_sheet_rows_api(primary_sid, extra_gid)

    if extra_rows:
        print(f"[WARRANTY] Extra rows (Sheets API): {len(extra_rows)}")
        _merge_rows_into_indexes(extra_rows, source_tag="extra")
        total_rows += len(extra_rows)
    elif EXTRA_WARRANTY_CSV_URL:
        try:
            rows2 = _fetch_csv_rows(EXTRA_WARRANTY_CSV_URL)
            print(f"[WARRANTY] Extra rows: {len(rows2)}")
            _merge_rows_into_indexes(rows2, source_tag="extra")
            total_rows += len(rows2)
        except Exception as e:
            print(f"[WARRANTY] Extra fetch failed: {e}")

    print(f"[WARRANTY] Loaded total rows: {total_rows}; "
          f"{len(WARRANTY_BY_DONGLE)} unique dongle ids; {len(WARRANTY_DB)} phone/serial keys.")

def warranty_lookup(identifier: str):
    """Legacy lookup by normalized phone/serial key."""
    return WARRANTY_DB.get(_norm_key(identifier))

def warranty_lookup_by_dongle(dongle_id: str):
    """Primary lookup by Dongle ID (merged)."""
    return WARRANTY_BY_DONGLE.get(_norm_dongle(dongle_id))

def warranty_text_from_row(row: dict) -> str:
    """
    Return a clean human answer using warranty-only columns.
    Looks for typical columns across both sheets.
    """
    # Common warranty columns across sheets
    status = _extract_field(row, "warranty", "warranty status", "subscription valid")
    end    = _extract_field(row, "warranty end", "warranty expiry", "subscription valid until")
    prod   = _extract_field(row, "prod date", "pd. date", "product date")
    sold   = _extract_field(row, "date of sale", "date", "sales date")
    inst   = _extract_field(row, "installation date", "date of installation")

    bits = []
    if status: bits.append(f"Status: {status}")
    if end:    bits.append(f"Ends: {end}")
    if sold:   bits.append(f"Purchased: {sold}")
    if inst:   bits.append(f"Installed: {inst}")
    if prod:   bits.append(f"Prod Date: {prod}")

    return " | ".join(bits) if bits else "Warranty info found."
