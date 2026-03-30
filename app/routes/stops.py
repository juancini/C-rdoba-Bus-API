from fastapi import APIRouter, HTTPException
from app.models import StopSearch, NextBuses, Stop

# This will be injected from main.py
gtfs_service = None

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get("/search", response_model=StopSearch)
def search_stops(q: str):
    """Search stops by name. E.g. /stops/search?q=nueva+córdoba"""
    results = gtfs_service.search_stops(q)
    if not results:
        raise HTTPException(status_code=404, detail="No stops found")
    return {"stops": results}


@router.get("/{stop_id}", response_model=Stop)
def get_stop(stop_id: str):
    """Get a single stop by ID."""
    stop = gtfs_service.get_stop(stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    return stop


@router.get("/{stop_id}/next-buses", response_model=NextBuses)
def next_buses(stop_id: str, limit: int = 5):
    """
    Get the next scheduled buses for a stop.
    Times are based on the static schedule (no realtime yet).
    """
    stop = gtfs_service.get_stop(stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    arrivals = gtfs_service.get_next_arrivals(stop_id, limit=limit)
    return {
        "stop": stop,
        "next_buses": arrivals,
    }


def set_service(service):
    """Inject the service instance (called from main.py)."""
    global gtfs_service
    gtfs_service = service
