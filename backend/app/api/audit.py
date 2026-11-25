from fastapi import APIRouter, HTTPException

from app.database.audit_db import (
    fetch_audit_logs,
    remove_audit_log,
    remove_all_audit_logs
)


router = APIRouter()


@router.get("/audit-logs")
def get_audit_logs(limit: int = 50):
    try:
        return fetch_audit_logs(limit)
    except Exception as e:
        return {
            "total": 0,
            "logs": [],
            "error": str(e)
        }


@router.delete("/audit-logs/{log_id}")
def delete_audit_log(log_id: int):
    try:
        deleted_count = remove_audit_log(log_id)

        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Log entry not found."
            )

        return {
            "message": "Audit log deleted successfully.",
            "id": log_id
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete("/audit-logs")
def clear_all_audit_logs():
    try:
        remove_all_audit_logs()

        return {
            "message": "All audit logs cleared successfully."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
