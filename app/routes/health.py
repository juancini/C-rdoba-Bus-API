from fastapi import APIRouter
from app.models import HealthCheck

# This will be injected from main.py
gtfs_service = None

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheck)
def health():
    """Health check endpoint with stop count."""
    return {
        "status": "ok",
        "stops_loaded": gtfs_service.get_stop_count(),
    }


def set_service(service):
    """Inject the service instance (called from main.py)."""
    global gtfs_service
    gtfs_service = service
