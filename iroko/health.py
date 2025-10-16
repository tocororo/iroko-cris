
# Optional: use a dedicated router (cleaner for large apps)
from fastapi import APIRouter


router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}
