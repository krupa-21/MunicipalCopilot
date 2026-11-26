
import psycopg2
from datetime import datetime

from app.core.config import DATABASE_URL


def _connect():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not configured."
        )

    return psycopg2.connect(DATABASE_URL)


def init_audit_db():
    connection = _connect()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    query TEXT NOT NULL,
                    answer_preview TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    response_time_ms DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL
                )
            """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


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

        connection = _connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_logs (
                        timestamp,
                        user_role,
                        query,
                        answer_preview,
                        sources,
                        response_time_ms,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        user_role,
                        query,
                        (answer[:250] + "...") if len(answer) > 250 else answer,
                        sources_str,
                        round(response_time_ms, 2),
                        status
                    )
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    except Exception as e:
        print(f"Audit log failed: {e}")


def fetch_audit_logs(limit: int = 50):
    connection = _connect()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM audit_logs
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,)
            )

            rows = cursor.fetchall()
            columns = [
                description[0]
                for description in cursor.description
            ]

            logs = [
                dict(zip(columns, row))
                for row in rows
            ]

            return {
                "total": len(logs),
                "logs": logs
            }

    finally:
        connection.close()


def remove_audit_log(log_id: int):
    connection = _connect()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM audit_logs WHERE id = %s",
                (log_id,)
            )

            deleted_count = cursor.rowcount

        connection.commit()
        return deleted_count

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def remove_all_audit_logs():
    connection = _connect()

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM audit_logs")

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
