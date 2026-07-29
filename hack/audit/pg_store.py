"""
hack/audit/pg_store.py
-----------------------
PostgresReportStore — drop-in replacement for ReportStore backed by
a Render Postgres instance (or any PostgreSQL database).

Activated automatically when DATABASE_URL is set in the environment.
Falls back to the file-backed ReportStore when DATABASE_URL is absent.

Schema (auto-created on first use, no migration tool needed):

    reports        — full ServiceAuditReport JSON + indexed fields
    certificates   — full SoulboundCertificate JSON + indexed fields
    pdfs           — binary PDF blobs keyed by report_id
    skills         — skill.md text keyed by report_id

No ORM. Raw psycopg2 with parameterised queries throughout.
"""

from __future__ import annotations

import json
import threading
from typing import Optional

try:
    import psycopg2                          # type: ignore
    import psycopg2.extras                   # type: ignore
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

from ..models.compliance import (
    CertificateSummary,
    ServiceAuditReport,
    SoulboundCertificate,
)


_DDL = """
CREATE TABLE IF NOT EXISTS reports (
    report_id   TEXT PRIMARY KEY,
    service_name TEXT NOT NULL DEFAULT '',
    score       REAL NOT NULL DEFAULT 0,
    grade       TEXT NOT NULL DEFAULT '',
    passed      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  BIGINT NOT NULL DEFAULT 0,
    data        JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS certificates (
    certificate_id  TEXT PRIMARY KEY,
    report_id       TEXT NOT NULL,
    agent_name      TEXT NOT NULL DEFAULT '',
    score           REAL NOT NULL DEFAULT 0,
    grade           TEXT NOT NULL DEFAULT '',
    minted_at       BIGINT NOT NULL DEFAULT 0,
    token_id        TEXT NOT NULL DEFAULT '',
    serial_number   INTEGER NOT NULL DEFAULT 0,
    hashscan_tx_url TEXT NOT NULL DEFAULT '',
    recipient_account_id TEXT NOT NULL DEFAULT '',
    service_endpoint TEXT,
    data            JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS pdfs (
    report_id TEXT PRIMARY KEY,
    content   BYTEA NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    report_id TEXT PRIMARY KEY,
    content   TEXT NOT NULL
);
"""


class PostgresReportStore:
    """
    PostgreSQL-backed report and certificate store.

    Args:
        database_url: A libpq connection string, e.g.
            "postgresql://user:pass@host:5432/dbname"
    """

    def __init__(self, database_url: str) -> None:
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "psycopg2 is not installed. Add it to pyproject.toml dependencies."
            )
        self._url = database_url
        self._lock = threading.Lock()
        self._conn: Optional[object] = None
        self._ensure_schema()

    # ── Connection management ────────────────────────────────────────────────

    def _get_conn(self):
        """Return a live connection, reconnecting if needed."""
        try:
            if self._conn is not None:
                # Quick health check
                self._conn.cursor().execute("SELECT 1")
                return self._conn
        except Exception:
            self._conn = None

        self._conn = psycopg2.connect(self._url)
        self._conn.autocommit = True
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(_DDL)

    # ── Reports ──────────────────────────────────────────────────────────────

    def save_report(self, report: ServiceAuditReport) -> None:
        data = json.loads(report.model_dump_json())
        conn = self._get_conn()
        with self._lock, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reports (report_id, service_name, score, grade, passed, created_at, data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (report_id) DO UPDATE SET
                    service_name = EXCLUDED.service_name,
                    score        = EXCLUDED.score,
                    grade        = EXCLUDED.grade,
                    passed       = EXCLUDED.passed,
                    data         = EXCLUDED.data
                """,
                (
                    report.report_id,
                    report.request.service_name,
                    report.overall_score,
                    report.grade,
                    report.passed,
                    report.created_at,
                    json.dumps(data),
                ),
            )

    def get_report(self, report_id: str) -> Optional[ServiceAuditReport]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM reports WHERE report_id = %s", (report_id,))
            row = cur.fetchone()
        if row is None:
            return None
        try:
            return ServiceAuditReport.model_validate(row[0])
        except Exception:
            return None

    # ── Certificates ─────────────────────────────────────────────────────────

    def save_certificate(self, cert: SoulboundCertificate) -> None:
        data = json.loads(cert.model_dump_json())
        conn = self._get_conn()
        with self._lock, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO certificates (
                    certificate_id, report_id, agent_name, score, grade,
                    minted_at, token_id, serial_number, hashscan_tx_url,
                    recipient_account_id, service_endpoint, data
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (certificate_id) DO UPDATE SET
                    data = EXCLUDED.data,
                    hashscan_tx_url = EXCLUDED.hashscan_tx_url,
                    score = EXCLUDED.score
                """,
                (
                    cert.certificate_id,
                    cert.report_id,
                    cert.agent_name,
                    cert.score,
                    cert.grade,
                    cert.minted_at,
                    cert.token_id,
                    cert.serial_number,
                    cert.hashscan_tx_url,
                    cert.recipient_account_id,
                    cert.service_endpoint,
                    json.dumps(data),
                ),
            )

    def get_certificate(self, cert_id: str) -> Optional[SoulboundCertificate]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data FROM certificates WHERE certificate_id = %s",
                (cert_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        try:
            return SoulboundCertificate.model_validate(row[0])
        except Exception:
            return None

    def list_certificates(self, limit: int = 100) -> list[CertificateSummary]:
        conn = self._get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT certificate_id, report_id, agent_name, score, grade,
                       minted_at, token_id, serial_number, hashscan_tx_url
                FROM certificates
                ORDER BY minted_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [CertificateSummary(**dict(row)) for row in rows]

    # ── PDFs ─────────────────────────────────────────────────────────────────

    def save_pdf(self, report_id: str, data: bytes):
        conn = self._get_conn()
        with self._lock, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pdfs (report_id, content) VALUES (%s, %s)
                ON CONFLICT (report_id) DO UPDATE SET content = EXCLUDED.content
                """,
                (report_id, psycopg2.Binary(data)),
            )
        # Return a dummy Path-like object so callers don't need to change
        return _FakePath(report_id)

    def get_pdf_path(self, report_id: str):
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM pdfs WHERE report_id = %s", (report_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return _FakePath(report_id, bytes(row[0]))

    # ── SKILL.md ─────────────────────────────────────────────────────────────

    def save_skill_md(self, report_id: str, text: str):
        conn = self._get_conn()
        with self._lock, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO skills (report_id, content) VALUES (%s, %s)
                ON CONFLICT (report_id) DO UPDATE SET content = EXCLUDED.content
                """,
                (report_id, text),
            )
        return _FakePath(report_id)

    def get_skill_path(self, report_id: str):
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM skills WHERE report_id = %s", (report_id,)
            )
            row = cur.fetchone()
        return _FakePath(report_id, row[0].encode() if row else None) if row else None


class _FakePath:
    """
    Minimal Path-like shim so PDF/skill routes work without file system changes.
    The audit router calls FileResponse(path) for PDFs — we override exists()
    and the binary read so it works transparently.
    """

    def __init__(self, name: str, content: bytes | None = None) -> None:
        self._name = name
        self._content = content

    def exists(self) -> bool:
        return self._content is not None

    def read_bytes(self) -> bytes:
        return self._content or b""

    def read_text(self, encoding: str = "utf-8") -> str:
        return (self._content or b"").decode(encoding)

    def __str__(self) -> str:
        return self._name

    def __fspath__(self) -> str:
        return self._name
