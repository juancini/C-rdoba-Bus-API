from typing import ClassVar

from pydantic import BaseModel

from .stop import Stop


class Arrival(BaseModel):
    """A single bus arrival at a stop."""

    trip_id: str
    route_id: str
    route_short_name: str
    headsign: str
    arrival_time: str
    minutes_away: int

    class Config:
        json_schema_extra: ClassVar = {
            "example": {
                "trip_id": "TRIP-001",
                "route_id": "R100",
                "route_short_name": "100",
                "headsign": "Cerro de las Rosas",
                "arrival_time": "14:30",
                "minutes_away": 5,
            }
        }


class NextBuses(BaseModel):
    """Next buses at a stop."""

    stop: Stop
    next_buses: list[Arrival]


class HealthCheck(BaseModel):
    """Health check response."""

    status: str
    stops_loaded: int
