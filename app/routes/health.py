from fastapi import APIRouter
from app.services.transfer_store import store
from app.cache.cache_manager import cache

router = APIRouter(tags=["System"])


@router.get("/health", summary="Health check")
def health():
    return {
        "status": "ok",
        "transfers_loaded": store.count(),
        "cache": cache.stats(),
    }
