from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.gtfs import GTFSData

gtfs = GTFSData()

@asynccontextmanager
async def lifespan(app: FastAPI):
    gtfs.load()
    yield

app = FastAPI(
    title="Córdoba Bus API",
    description="Static schedule API for Córdoba, Argentina urban buses",
    lifespan=lifespan,
)

@app.get("/health")
def health():
    return {"status": "ok", "stops_loaded": len(gtfs.stops)}

@app.get("/stops/search")
def search_stops(q: str):
    """Search stops by name. E.g. /stops/search?q=nueva+córdoba"""
    results = gtfs.search_stops(q)
    if not results:
        raise HTTPException(status_code=404, detail="No stops found")
    return results

@app.get("/stops/{stop_id}")
def get_stop(stop_id: str):
    """Get a single stop by ID."""
    stop = gtfs.stops.get(stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    return stop

@app.get("/stops/{stop_id}/next-buses")
def next_buses(stop_id: str, limit: int = 5):
    """
    Get the next scheduled buses for a stop.
    Times are based on the static schedule (no realtime yet).
    """
    if stop_id not in gtfs.stops:
        raise HTTPException(status_code=404, detail="Stop not found")
    arrivals = gtfs.next_arrivals(stop_id, limit=limit)
    return {
        "stop": gtfs.stops[stop_id],
        "next_buses": arrivals,
    }

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
