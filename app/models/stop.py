from typing import ClassVar

from pydantic import BaseModel


class Stop(BaseModel):
    """A single bus stop."""

    stop_id: str
    name: str
    lat: float
    lon: float

    class Config:
        json_schema_extra: ClassVar = {
            "example": {
                "stop_id": "1001",
                "name": "Nueva Córdoba - Centro",
                "lat": -31.405,
                "lon": -64.188,
            }
        }


class StopSearch(BaseModel):
    """Search results for stops."""

    stops: list[Stop]
