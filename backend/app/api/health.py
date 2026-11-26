from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    return {
        "message": "Municipal Knowledge Copilot API is running!",
        "status": "success"
    }
