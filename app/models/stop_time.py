from pydantic import BaseModel


class StopTime(BaseModel):
    """Internal model for stop times with arrival seconds for sorting."""

    trip_id: str
    route_id: str
    route_short_name: str
    headsign: str
    arrival_seconds: int
    arrival_time: str
