from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.repositories import GTFSRepository
from app.services import GTFSService
from app.routes import stops, routes, health

# Initialize repository and service
repository = GTFSRepository()
gtfs_service = GTFSService(repository)

# Inject service into route handlers
stops.set_service(gtfs_service)
routes.set_service(gtfs_service)
health.set_service(gtfs_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load GTFS data on startup."""
    repository.load()
    yield


app = FastAPI(
    title="Córdoba Bus API",
    description="Static schedule API for Córdoba, Argentina urban buses",
    lifespan=lifespan,
)

# Register routers
app.include_router(health.router)
app.include_router(stops.router)
app.include_router(routes.router)


@app.get("/routes")
def list_routes():
    """List all routes."""
    return list(gtfs.routes.values())


@app.get("/routes/{route_id}/stops")
def route_stops(route_id: str):
    """List all stops for a route."""
    stops = gtfs.stops_for_route(route_id)
    if not stops:
        raise HTTPException(status_code=404, detail="Route not found")
    return stops
