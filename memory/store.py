import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from schemas.engagement import EngagementResult, PostRecord
from schemas.reports import Finding, ObservationReport


DB_PATH = Path("memory/social_intel.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS post_records (
                post_id           TEXT PRIMARY KEY,
                platform          TEXT NOT NULL,
                generated_content TEXT NOT NULL,
                approved_content  TEXT NOT NULL,
                posted_at         TEXT,
                platform_post_id  TEXT,
                engagement_result TEXT,
                experiment_id     TEXT,
                created_at        TEXT NOT NULL
            )
        """)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(post_records)").fetchall()]
        if "platform_post_id" not in cols:
            conn.execute("ALTER TABLE post_records ADD COLUMN platform_post_id TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_reports (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                platform         TEXT NOT NULL,
                generated_at     TEXT NOT NULL,
                top_priority     TEXT NOT NULL,
                recommendations  TEXT NOT NULL,
                findings         TEXT NOT NULL
            )
        """)


def save_post_record(record: PostRecord) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO post_records
                (post_id, platform, generated_content, approved_content,
                 posted_at, platform_post_id, engagement_result, experiment_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.post_id,
                record.platform,
                record.generated_content,
                record.approved_content,
                record.posted_at.isoformat() if record.posted_at else None,
                record.platform_post_id,
                json.dumps(record.engagement_result.__dict__) if record.engagement_result else None,
                record.experiment_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def update_platform_post_id(post_id: str, platform_post_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE post_records SET platform_post_id = ? WHERE post_id = ?",
            (platform_post_id, post_id),
        )


def update_engagement(post_id: str, result: EngagementResult) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE post_records SET engagement_result = ? WHERE post_id = ?",
            (json.dumps(result.__dict__), post_id),
        )


def get_post_records() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM post_records ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def save_analysis_report(report: ObservationReport) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO analysis_reports
               (platform, generated_at, top_priority, recommendations, findings)
               VALUES (?, ?, ?, ?, ?)""",
            (
                report.platform,
                report.generated_at.isoformat(),
                report.top_priority,
                json.dumps(report.recommendations),
                json.dumps([{
                    "category": f.category,
                    "observation": f.observation,
                    "signal_strength": f.signal_strength,
                } for f in report.findings]),
            ),
        )


def get_latest_analysis(platform: str = "linkedin") -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM analysis_reports
               WHERE platform = ? ORDER BY generated_at DESC LIMIT 1""",
            (platform,),
        ).fetchone()
    if not row:
        return None
    return {
        "platform": row["platform"],
        "generated_at": row["generated_at"],
        "top_priority": row["top_priority"],
        "recommendations": json.loads(row["recommendations"]),
        "findings": json.loads(row["findings"]),
    }
