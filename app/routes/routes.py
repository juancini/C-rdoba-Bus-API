from fastapi import APIRouter

from app.models import Route, RouteStops

# This will be injected from main.py
gtfs_service = None

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=list[Route])
def list_routes():
    """List all routes."""
    return gtfs_service.get_all_routes()


@router.get("/{route_id}/stops", response_model=RouteStops)
def get_route_stops(route_id: str):
    """Get all stops along a route in order."""
    route_data = gtfs_service.repo.routes.get(route_id)
    if not route_data:
        return {"error": "Route not found"}

    route = Route(**route_data)
    stops = gtfs_service.get_stops_for_route(route_id)

    return {
        "route": route,
        "stops": stops,
    }


def set_service(service):
    """Inject the service instance (called from main.py)."""
    global gtfs_service
    gtfs_service = service
