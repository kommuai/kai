#!/usr/bin/env python3
"""Restore or seed Shadou Studio admin.db.

Usage:
  # Copy an existing backup:
  python3 scripts/restore_admin_db.py /path/to/admin.db

  # Seed from shadou-tenant-* dirs + optional user (no backup file):
  STUDIO_SEED_EMAIL=you@example.com STUDIO_SEED_PASSWORD='your-pass' \\
    python3 scripts/restore_admin_db.py --seed

Run from studio/backend/ (or pass --db-dir).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow running as script from backend/
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from auth import hash_password  # noqa: E402
from database import init_db  # noqa: E402
from shadou_paths import shadou_tenants_root  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

DB_DIR = Path(os.getenv("SHADOU_ADMIN_DB_DIR", _BACKEND / "data"))
DB_PATH = DB_DIR / "admin.db"

TENANT_DESCRIPTIONS: dict[str, str] = {
    "kommu": (
        "Kommu — a Malaysian company that makes KommuAssist, an advanced driving assistance system "
        "(ADAS aftermarket device) based on openpilot / bukapilot."
    ),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def backup_current() -> Path | None:
    if not DB_PATH.is_file():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = DB_DIR / f"admin.db.bak-{stamp}"
    shutil.copy2(DB_PATH, dest)
    return dest


def restore_from_file(src: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"Not a file: {src}")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, DB_PATH)
    print(f"Restored {src} -> {DB_PATH}")
    init_db()
    print("Ran init_db() migrations on restored database.")


def discover_tenant_dirs(root: Path) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    if not root.is_dir():
        return out
    for p in sorted(root.glob("shadou-tenant-*")):
        if p.is_dir():
            slug = p.name.removeprefix("shadou-tenant-")
            out.append((slug, p.resolve()))
    return out


def seed(
    email: str,
    password: str,
    name: str,
    tenant_slugs: list[str] | None,
) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    init_db()

    root = shadou_tenants_root()
    discovered = discover_tenant_dirs(root)
    by_slug = {s: p for s, p in discovered}

    if tenant_slugs:
        pairs = []
        for slug in tenant_slugs:
            if slug not in by_slug:
                print(f"Warning: no folder shadou-tenant-{slug} under {root}", file=sys.stderr)
                continue
            pairs.append((slug, by_slug[slug]))
    else:
        pairs = discovered

    if not pairs:
        raise SystemExit(f"No shadou-tenant-* directories under {root}")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)
    now = _now_iso()

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE lower(email) = lower(:e)"),
            {"e": email},
        ).fetchone()
        if row:
            user_id = row[0]
            conn.execute(
                text(
                    "UPDATE users SET password_hash = :h, provider = 'email', name = :n WHERE id = :id"
                ),
                {"h": pw_hash, "n": name, "id": user_id},
            )
            print(f"Updated password for existing user {email}")
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO users (id, email, name, avatar_url, password_hash, provider, provider_id, is_verified, created_at)
                    VALUES (:id, :email, :name, '', :h, 'email', '', 1, :now)
                    """
                ),
                {"id": user_id, "email": email, "name": name, "h": pw_hash, "now": now},
            )
            print(f"Created user {email}")

        for slug, path in pairs:
            existing = conn.execute(
                text("SELECT id FROM tenants WHERE slug = :s"),
                {"s": slug},
            ).fetchone()
            desc = TENANT_DESCRIPTIONS.get(slug, "")
            if existing:
                tid = existing[0]
                conn.execute(
                    text(
                        """
                        UPDATE tenants SET owner_id = :uid, workspace_home = :home,
                        description = CASE WHEN :desc != '' THEN :desc ELSE description END,
                        updated_at = :now
                        WHERE id = :tid
                        """
                    ),
                    {"uid": user_id, "home": str(path), "tid": tid, "now": now, "desc": desc},
                )
                print(f"Updated tenant slug={slug}")
            else:
                tid = str(uuid.uuid4())
                display = slug.replace("-", " ").title()
                conn.execute(
                    text(
                        """
                        INSERT INTO tenants (id, owner_id, slug, display_name, description, workspace_home, created_at, updated_at)
                        VALUES (:id, :uid, :slug, :dn, :desc, :home, :now, :now)
                        """
                    ),
                    {
                        "id": tid,
                        "uid": user_id,
                        "slug": slug,
                        "dn": display,
                        "desc": desc,
                        "home": str(path),
                        "now": now,
                    },
                )
                print(f"Created tenant slug={slug} -> {path}")

            conn.execute(
                text(
                    """
                    INSERT OR IGNORE INTO tenant_memberships (id, tenant_id, user_id, role, created_at)
                    SELECT lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' ||
                           lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' ||
                           lower(hex(randomblob(6))),
                           t.id, :uid, 'owner', :now
                    FROM tenants t WHERE t.slug = :slug
                    """
                ),
                {"uid": user_id, "slug": slug, "now": now},
            )

    print(f"\nDone. Database: {DB_PATH}")
    print(f"Sign in at Studio with {email} and the password you set in STUDIO_SEED_PASSWORD.")


def main() -> None:
    p = argparse.ArgumentParser(description="Restore or seed Shadou Studio admin.db")
    p.add_argument("source", nargs="?", help="Path to admin.db backup to copy in")
    p.add_argument("--seed", action="store_true", help="Seed from shadou-tenant-* dirs")
    p.add_argument("--email", default=os.getenv("STUDIO_SEED_EMAIL", "yuanting@kommu.ai"))
    p.add_argument("--name", default=os.getenv("STUDIO_SEED_NAME", "Yuanting"))
    p.add_argument("--password", default=os.getenv("STUDIO_SEED_PASSWORD"))
    p.add_argument(
        "--tenants",
        default=os.getenv("STUDIO_SEED_TENANTS", ""),
        help="Comma-separated slugs (default: all shadou-tenant-* under SHADOU_TENANTS_ROOT)",
    )
    p.add_argument("--no-backup", action="store_true", help="Skip backing up current admin.db")
    args = p.parse_args()

    if args.source and not args.seed:
        if args.source == "--seed":
            args.seed = True
        else:
            if not args.no_backup:
                b = backup_current()
                if b:
                    print(f"Backed up current DB to {b}")
            restore_from_file(Path(args.source).expanduser().resolve())
            return

    if args.seed or not args.source:
        if not args.password:
            raise SystemExit(
                "Set STUDIO_SEED_PASSWORD (or --password) for --seed. "
                "Example: STUDIO_SEED_PASSWORD='your-new-password' python3 scripts/restore_admin_db.py --seed"
            )
        if not args.no_backup:
            b = backup_current()
            if b:
                print(f"Backed up current DB to {b}")
        slugs = [s.strip() for s in args.tenants.split(",") if s.strip()] or None
        seed(args.email, args.password, args.name, slugs)
        return

    raise SystemExit("Provide a backup file path or use --seed")


if __name__ == "__main__":
    main()
