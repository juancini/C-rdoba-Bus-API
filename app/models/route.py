from typing import ClassVar

from pydantic import BaseModel

from .stop import Stop


class Route(BaseModel):
    """A bus route."""

    route_id: str
    short_name: str
    long_name: str
    type: str

    class Config:
        json_schema_extra: ClassVar = {
            "example": {
                "route_id": "R100",
                "short_name": "100",
                "long_name": "Centro - Cerro de las Rosas",
                "type": "3",
            }
        }


class RouteStops(BaseModel):
    """Route with its ordered stops."""

    route: Route
    stops: list[Stop]
