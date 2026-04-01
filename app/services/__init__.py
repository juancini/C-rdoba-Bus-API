from app.models import Arrival, Route, Stop
from app.repositories import GTFSRepository
from app.utils import get_now_seconds


class GTFSService:
    """Business logic layer. Implements features using the repository."""

    def __init__(self, repository: GTFSRepository):
        self.repo = repository

    def search_stops(self, query: str) -> list[Stop]:
        """Search stops by name."""
        q = query.lower()
        results = [s for s in self.repo.stops.values() if q in s.name.lower()]
        return results

    def get_stop(self, stop_id: str) -> Stop | None:
        """Get a single stop by ID."""
        return self.repo.stops.get(stop_id)

    def get_next_arrivals(self, stop_id: str, limit: int = 5) -> list[Arrival]:
        """Get the next arrivals at a stop from now."""
        now = get_now_seconds()
        stop_times = self.repo.stop_times.get(stop_id, [])

        upcoming = [a for a in stop_times if a.arrival_seconds >= now]
        if len(upcoming) < limit:
            upcoming += stop_times[:limit]  # wrap around midnight

        result = []
        for st in upcoming[:limit]:
            diff = st.arrival_seconds - now
            if diff < 0:
                diff += 86400

            arrival = Arrival(
                trip_id=st.trip_id,
                route_id=st.route_id,
                route_short_name=st.route_short_name,
                headsign=st.headsign,
                arrival_time=st.arrival_time,
                minutes_away=round(diff / 60),
            )
            result.append(arrival)

        return result

    def get_all_routes(self) -> list[Route]:
        """Get all routes."""
        return list(self.repo.routes.values())

    def get_stops_for_route(self, route_id: str) -> list[Stop]:
        """Get ordered stops for a route."""
        trip = next(
            (t for t in self.repo.trips.values() if t.route_id == route_id),
            None,
        )
        if not trip:
            return []

        trip_id = trip.trip_id
        seq = sorted(
            self.repo._trip_stop_seq.get(trip_id, []),
            key=lambda x: x["stop_sequence"],
        )
        return [
            self.repo.stops[s["stop_id"]]
            for s in seq
            if s["stop_id"] in self.repo.stops
        ]

    def get_stop_count(self) -> int:
        """Get total number of loaded stops."""
        return len(self.repo.stops)
