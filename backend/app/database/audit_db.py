import sqlite3
from datetime import datetime

from app.core.config import AUDIT_DB_PATH


def init_audit_db():
    try:
        with sqlite3.connect(AUDIT_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    query TEXT NOT NULL,
                    answer_preview TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    response_time_ms REAL NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"Error initializing audit db: {e}")


def log_audit(
    user_role: str,
    query: str,
    answer: str,
    sources: list,
    response_time_ms: float,
    status: str = "SUCCESS"
):
    try:
        sources_str = ", ".join(
            [
                f"{s.get('document', '')} (p.{s.get('page', '')})"
                for s in sources
            ]
        ) if sources else "None"

        with sqlite3.connect(AUDIT_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO audit_logs (timestamp, user_role, query, answer_preview, sources, response_time_ms, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_role,
                    query,
                    (answer[:250] + "...") if len(answer) > 250 else answer,
                    sources_str,
                    round(response_time_ms, 2),
                    status
                )
            )
            conn.commit()
    except Exception as e:
        print(f"Audit log failed: {e}")


init_audit_db()

def fetch_audit_logs(limit: int = 50):
    with sqlite3.connect(AUDIT_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()

        return {
            "total": len(rows),
            "logs": [dict(row) for row in rows]
        }


def remove_audit_log(log_id: int):
    with sqlite3.connect(AUDIT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM audit_logs WHERE id = ?",
            (log_id,)
        )
        conn.commit()
        return cursor.rowcount


def remove_all_audit_logs():
    with sqlite3.connect(AUDIT_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_logs")
        conn.commit()
