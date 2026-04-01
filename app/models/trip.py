from pydantic import BaseModel


class Trip(BaseModel):
    """A bus trip."""

    trip_id: str
    route_id: str
    service_id: str
    headsign: str
