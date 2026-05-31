"""Database setup."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from models import Base

DB_DIR = Path(os.getenv("SHADOU_ADMIN_DB_DIR", Path(__file__).parent / "data"))
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR / 'admin.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    # Minimal migration: create tenant_memberships + backfill owners.
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS tenant_memberships (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  user_id TEXT NOT NULL,
                  role TEXT NOT NULL DEFAULT 'owner',
                  created_at DATETIME,
                  CONSTRAINT uq_tenant_membership UNIQUE (tenant_id, user_id),
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                  FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tenant_memberships_tenant_id ON tenant_memberships(tenant_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tenant_memberships_user_id ON tenant_memberships(user_id)"))

        # Backfill from tenants.owner_id if missing.
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO tenant_memberships (id, tenant_id, user_id, role, created_at)
                SELECT
                  lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(2))) || '-' ||
                  lower(hex(randomblob(2))) || '-' || lower(hex(randomblob(6))) AS id,
                  t.id AS tenant_id,
                  t.owner_id AS user_id,
                  'owner' AS role,
                  COALESCE(t.created_at, CURRENT_TIMESTAMP) AS created_at
                FROM tenants t
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS tenant_invites (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  email TEXT NOT NULL,
                  token TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'pending',
                  created_by_user_id TEXT NOT NULL,
                  created_at DATETIME,
                  expires_at DATETIME,
                  CONSTRAINT uq_tenant_invite_token UNIQUE (token),
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                  FOREIGN KEY(created_by_user_id) REFERENCES users(id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tenant_invites_tenant_id ON tenant_invites(tenant_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tenant_invites_email ON tenant_invites(email)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS contact_tags (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  user_id TEXT NOT NULL,
                  tag TEXT NOT NULL,
                  created_at DATETIME,
                  CONSTRAINT uq_contact_tag UNIQUE (tenant_id, user_id, tag),
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contact_tags_tenant_id ON contact_tags(tenant_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contact_tags_user_id ON contact_tags(user_id)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS llm_usage_events (
                  id TEXT PRIMARY KEY,
                  tenant_slug TEXT,
                  source TEXT NOT NULL,
                  model TEXT NOT NULL,
                  prompt_tokens INTEGER NOT NULL DEFAULT 0,
                  completion_tokens INTEGER NOT NULL DEFAULT 0,
                  cached_prompt_tokens INTEGER NOT NULL DEFAULT 0,
                  total_tokens INTEGER NOT NULL DEFAULT 0,
                  cost_usd REAL NOT NULL,
                  pricing_model_key TEXT NOT NULL,
                  created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_llm_usage_events_created_at ON llm_usage_events(created_at)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_llm_usage_events_tenant_slug ON llm_usage_events(tenant_slug)")
        )

        for col, ddl in (
            ("training_job", "TEXT NOT NULL DEFAULT 'customer_support'"),
            ("training_level", "INTEGER NOT NULL DEFAULT 0"),
            ("training_level_title", "TEXT NOT NULL DEFAULT ''"),
            ("training_level_emoji", "TEXT NOT NULL DEFAULT ''"),
            ("training_progress_pct", "REAL NOT NULL DEFAULT 0"),
            ("training_last_assessed_at", "DATETIME"),
            ("training_badges_json", "TEXT NOT NULL DEFAULT '[]'"),
        ):
            try:
                conn.execute(text(f"ALTER TABLE tenants ADD COLUMN {col} {ddl}"))
            except Exception:
                pass

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS agent_training_runs (
                  id TEXT PRIMARY KEY,
                  tenant_id TEXT NOT NULL,
                  level_number INTEGER NOT NULL DEFAULT 0,
                  passed INTEGER NOT NULL DEFAULT 0,
                  gates_json TEXT NOT NULL DEFAULT '{}',
                  summary_json TEXT NOT NULL DEFAULT '{}',
                  duration_ms INTEGER NOT NULL DEFAULT 0,
                  triggered_by_user_id TEXT NOT NULL DEFAULT '',
                  created_at DATETIME,
                  FOREIGN KEY(tenant_id) REFERENCES tenants(id)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_agent_training_runs_tenant_id ON agent_training_runs(tenant_id)"
            )
        )


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
