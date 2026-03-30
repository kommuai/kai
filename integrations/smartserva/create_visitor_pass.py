#!/usr/bin/env python3
"""
Create a SMARTSERVA visitor pass from date/time inputs.

Visitor name and phone sent to SmartServa are fixed (Kommu / "1") for consistent listing lookup.

Usage:
  python3 create_visitor_pass.py --date 2026-03-28 --time 18:30
  python3 create_visitor_pass.py   # defaults to current local date/time

Credentials are read from environment variables:
  SMARTSERVA_USERNAME
  SMARTSERVA_PASSWORD
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import ddddocr
import requests

BASE_URL = "https://emhub.smartserva.com"

# Fixed visitor identity for Emhub passes (requested: name + phone literal "1").
SMARTSERVA_VISITOR_NAME = "Kommu"
SMARTSERVA_VISITOR_PHONE = "1"


def _local_now() -> dt.datetime:
    # Subprocess may only inherit `TZ` (Docker); Kai also uses `TZ_REGION` in config.
    tz_name = (os.getenv("TZ_REGION") or os.getenv("TZ") or "Asia/Kuala_Lumpur").strip()
    return dt.datetime.now(ZoneInfo(tz_name))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create visitor pass link (visitor name/phone fixed for Kommu automation)."
    )
    parser.add_argument(
        "--date",
        required=False,
        default="",
        help="Visit date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--time",
        required=False,
        default="",
        help="Visit time in HH:MM format (24h) (default: current time)",
    )
    parser.add_argument(
        "--unit-id",
        default=None,
        help="Optional unit id override. If omitted, tool uses first unit from account.",
    )
    parser.add_argument(
        "--max-login-attempts",
        type=int,
        default=12,
        help="Max captcha/login attempts before failing",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout seconds",
    )
    return parser.parse_args()


def require_credentials() -> Tuple[str, str]:
    username = os.getenv("SMARTSERVA_USERNAME", "").strip()
    password = os.getenv("SMARTSERVA_PASSWORD", "").strip()
    if not username or not password:
        raise RuntimeError(
            "Missing credentials. Set SMARTSERVA_USERNAME and SMARTSERVA_PASSWORD."
        )
    return username, password


def parse_schedule(date_raw: str, time_raw: str) -> Tuple[str, str, str]:
    now = _local_now()
    date_raw = (date_raw or "").strip()
    time_raw = (time_raw or "").strip()
    visit_date = dt.datetime.strptime(date_raw, "%Y-%m-%d").date() if date_raw else now.date()
    if time_raw:
        visit_time = dt.datetime.strptime(time_raw, "%H:%M").time()
    else:
        # SmartServa blocks appointments outside booking window (06:00-22:00).
        # When caller omits time, auto-pick a safe default inside the valid window.
        if now.hour >= 22:
            visit_date = visit_date + dt.timedelta(days=1)
            visit_time = dt.time(hour=10, minute=0)
        elif now.hour < 6:
            visit_time = dt.time(hour=10, minute=0)
        else:
            visit_time = now.time()
    date_dd_mmm = visit_date.strftime("%d-%b-%Y")

    # Convert to 5-minute slot index (0..287), rounded to nearest lower step.
    slot = (visit_time.hour * 60 + visit_time.minute) // 5
    slot = max(0, min(287, slot))
    return date_dd_mmm, str(slot), visit_time.strftime("%H:%M")


def build_session(timeout: int) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "smartserva-automation/1.0",
            "Accept": "application/json, text/plain, */*",
        }
    )
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


def request(s: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    timeout = getattr(s, "request_timeout", 30)
    return s.request(method, url, timeout=timeout, **kwargs)


def login_with_captcha(
    s: requests.Session, username: str, password: str, max_attempts: int
) -> None:
    ocr = ddddocr.DdddOcr(show_ad=False)
    for attempt in range(1, max_attempts + 1):
        page = request(s, "GET", f"{BASE_URL}/app.php")
        html = page.text
        m = re.search(
            r'<img src="([^"]*/capt\.php\?t=[^"]+)" class="capt_img" t="1">',
            html,
            re.I,
        )
        if not m:
            continue
        captcha_url = f"{BASE_URL}{m.group(1)}"
        captcha_img = request(s, "GET", captcha_url).content
        pred = ocr.classification(captcha_img) or ""
        pred = "".join(ch for ch in pred.strip() if ch.isalnum())
        if not pred:
            continue

        payload = {
            "username": username,
            "password": password,
            "capt": pred,
            "action": "login",
            "p": "",
            "ax": "2",
            "app": "2",
            "appt": "u",
        }
        resp = request(s, "POST", f"{BASE_URL}/process.php", data=payload)
        try:
            data = resp.json()
        except Exception:
            continue

        if data.get("s") == 2:
            return

        msg = str(data.get("msg", "")).lower()
        if "wrong username or password" in msg:
            raise RuntimeError("Login failed: username/password rejected by server.")

    raise RuntimeError("Login failed after captcha retry budget.")


def discover_unit_id(s: requests.Session) -> str:
    resp = request(
        s,
        "POST",
        f"{BASE_URL}/process3.php",
        data={"fs": "0", "action": "check_login", "appt": "u", "pid": "-1"},
    )
    data = resp.json()
    units_html = str(data.get("units", ""))
    m = re.search(r"<option value=\"(\d+)\"", units_html)
    if not m:
        raise RuntimeError("Unable to discover unit id from account data.")
    return m.group(1)


def create_visitor(
    s: requests.Session,
    unit_id: str,
    appoint_date_dd_mmm: str,
    slot: str,
    visitor_name: str,
    visitor_phone: str,
) -> Dict[str, object]:
    # Warm up visitor validity computation used by frontend.
    request(
        s,
        "POST",
        f"{BASE_URL}/process2.php",
        data={
            "fs": "0",
            "action": "get_ov",
            "sd": appoint_date_dd_mmm,
            "sh": slot,
            "ov": "1",
            "v": "3",
            "chg_vt": "0",
            "ed": appoint_date_dd_mmm,
            "unit": unit_id,
        },
    )

    payload = {
        "appoint_d": appoint_date_dd_mmm,
        "nm": visitor_name,
        "tel": visitor_phone,
        "tel_ex": "my_60",
        "carplate": "",
        "vt": "3",  # Delivery
        "ov": "1",
        "sh": slot,
        "ed": appoint_date_dd_mmm,
        "cp_req_v": "",
        "fa_req_v": "",
        "p": "2",
        "app": "2",
        "unit": unit_id,
        "unit_v": unit_id,
        "action": "add_vi",
        "category": "1",
    }
    resp = request(
        s,
        "POST",
        f"{BASE_URL}/process2.php",
        files={k: (None, v) for k, v in payload.items()},
    )
    data = resp.json()
    if data.get("s") != 2:
        raise RuntimeError(f"Visitor creation failed: {data}")
    return data


def find_created_visitor_id(s: requests.Session, visitor_name: str) -> Optional[Tuple[str, str]]:
    resp = request(
        s,
        "POST",
        f"{BASE_URL}/process3.php",
        data={"fs": "0", "action": "get_vi", "t": "vi_reg", "pg": "1", "pid": "-1", "auth": "2"},
    )
    data = resp.json()
    html = str(data.get("v", ""))
    rows = re.findall(
        r'<tr class="vi_r_c vi_r" v="(\d+)">[\s\S]*?<div class="vi_nm">([^<]+)</div>[\s\S]*?<td class="vi_r_status"[^>]*>([^<]+)</td>',
        html,
        re.I,
    )
    for rid, nm, status in rows:
        if nm.strip().lower() == visitor_name.strip().lower():
            return rid, status.strip()
    return None


def get_visitor_link(s: requests.Session, visitor_id: str) -> Optional[str]:
    resp = request(
        s,
        "POST",
        f"{BASE_URL}/process2.php",
        data={"action": "get_vi_dt", "v": visitor_id, "t": "", "app": "2", "upn": "0"},
    )
    data = resp.json()
    if data.get("s") != 2:
        # Fallback: sometimes API may return non-2 with embedded URL text.
        packed = json.dumps(data, ensure_ascii=False)
        m = re.search(r"https?://[^\s\"'<>]+", packed)
        return m.group(0) if m else None
    link = str(data.get("qr_link", "")).strip()
    if link:
        return link

    # Fallback: some accounts return link only inside share HTML snippets.
    for key in ("share", "share_list", "share_copy"):
        raw = str(data.get(key, ""))
        m = re.search(r"https?://[^\s\"'<>]+", raw)
        if m:
            return m.group(0)
    return None


def main() -> int:
    args = parse_args()
    username, password = require_credentials()
    appoint_date_dd_mmm, slot, time_hhmm = parse_schedule(args.date, args.time)

    visitor_name = SMARTSERVA_VISITOR_NAME
    visitor_phone = SMARTSERVA_VISITOR_PHONE

    session = build_session(args.timeout)
    login_with_captcha(session, username, password, args.max_login_attempts)

    unit_id = args.unit_id or discover_unit_id(session)
    create_visitor(
        s=session,
        unit_id=unit_id,
        appoint_date_dd_mmm=appoint_date_dd_mmm,
        slot=slot,
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
    )

    created = find_created_visitor_id(session, visitor_name)
    if not created:
        raise RuntimeError("Created visitor row not found in registrations list.")
    visitor_id, status = created

    link = None
    for _ in range(8):
        link = get_visitor_link(session, visitor_id)
        if link:
            break
        time.sleep(0.75)
    if not link:
        raise RuntimeError("Visitor created but pass link not found.")

    out = {
        "ok": True,
        "visit_date": appoint_date_dd_mmm,
        "visit_time": time_hhmm,
        "valid_from_slot": slot,
        "visitor_name": visitor_name,
        "visitor_phone": visitor_phone,
        "visitor_id": visitor_id,
        "status": status,
        "visitor_pass_link": link,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
