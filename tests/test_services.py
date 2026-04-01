"""Unit tests for GTFSService business logic layer."""

import pytest

from app.models import Arrival, Stop
from app.repositories import GTFSRepository
from app.services import GTFSService
from app.utils import get_now_seconds


class TestGTFSService:
    """Test the GTFSService class for business logic."""

    @pytest.fixture
    def service(self, test_db_with_data, sample_stops, sample_routes, sample_trips):
        """Create a GTFSService instance with test data."""
        repo = GTFSRepository()
        repo.stops = sample_stops
        repo.routes = sample_routes
        repo.trips = sample_trips
        repo.stop_times = repo.stop_times.__class__(test_db_with_data)
        repo._trip_stop_seq = repo._trip_stop_seq.__class__(test_db_with_data)
        return GTFSService(repo)

    def test_search_stops_by_name(self, service):
        """Test searching stops by partial name match."""
        results = service.search_stops("centro")
        assert len(results) == 1
        assert results[0].stop_id == "1001"
        assert "Centro" in results[0].name

    def test_search_stops_case_insensitive(self, service):
        """Test that search is case-insensitive."""
        results_lower = service.search_stops("centro")
        results_upper = service.search_stops("CENTRO")
        assert len(results_lower) == len(results_upper) == 1

    def test_search_stops_no_results(self, service):
        """Test search with no matching stops."""
        results = service.search_stops("nonexistent")
        assert results == []

    def test_search_stops_multiple_results(self, service):
        """Test search that returns multiple stops."""
        results = service.search_stops("a")  # Matches all stops with "a"
        assert len(results) >= 1

    def test_get_stop_existing(self, service):
        """Test getting an existing stop by ID."""
        stop = service.get_stop("1001")
        assert stop is not None
        assert stop.stop_id == "1001"
        assert stop.name == "Centro - Plaza San Martín"

    def test_get_stop_nonexistent(self, service):
        """Test getting a non-existent stop."""
        stop = service.get_stop("9999")
        assert stop is None

    def test_get_all_routes(self, service):
        """Test getting all routes."""
        routes = service.get_all_routes()
        assert len(routes) == 2
        route_ids = [r.route_id for r in routes]
        assert "R100" in route_ids
        assert "R200" in route_ids

    def test_get_stops_for_route(self, service):
        """Test getting ordered stops for a route."""
        stops = service.get_stops_for_route("R100")
        assert len(stops) == 3
        # Verify stops are in correct order (1001, 1002, 1003)
        stop_ids = [s.stop_id for s in stops]
        assert stop_ids == ["1001", "1002", "1003"]

    def test_get_stops_for_nonexistent_route(self, service):
        """Test getting stops for a non-existent route."""
        stops = service.get_stops_for_route("R999")
        assert stops == []

    def test_get_next_arrivals_format(self, service):
        """Test that next arrivals returns Arrival objects."""
        arrivals = service.get_next_arrivals("1001")
        assert len(arrivals) > 0
        assert all(isinstance(a, Arrival) for a in arrivals)

    def test_get_next_arrivals_has_minutes_away(self, service):
        """Test that arrivals include minutes_away calculation."""
        arrivals = service.get_next_arrivals("1001")
        first_arrival = arrivals[0]
        assert hasattr(first_arrival, "minutes_away")
        assert isinstance(first_arrival.minutes_away, int)

    def test_get_next_arrivals_limit(self, service):
        """Test that limit parameter works correctly."""
        arrivals_5 = service.get_next_arrivals("1001", limit=5)
        arrivals_2 = service.get_next_arrivals("1001", limit=2)

        assert len(arrivals_5) <= 5
        assert len(arrivals_2) <= 2

    def test_get_next_arrivals_nonexistent_stop(self, service):
        """Test getting arrivals for non-existent stop."""
        arrivals = service.get_next_arrivals("9999")
        assert arrivals == []

    def test_get_stop_count(self, service):
        """Test getting total number of stops."""
        count = service.get_stop_count()
        assert count == 3  # We have 3 sample stops

    def test_arrival_has_route_info(self, service):
        """Test that arrivals include route information."""
        arrivals = service.get_next_arrivals("1001", limit=1)
        arrival = arrivals[0]
        assert arrival.route_id
        assert arrival.route_short_name
        assert arrival.headsign
        assert arrival.arrival_time

    def test_arrivals_sorted_by_time(self, service):
        """Test that arrivals are returned in chronological order."""
        arrivals = service.get_next_arrivals("1001", limit=3)

        if len(arrivals) > 1:
            # Extract hours:minutes for comparison
            times = [int(a.arrival_time.split(":")[0]) for a in arrivals]
            # Should be in ascending order (or wrap around midnight)
            for i in range(len(times) - 1):
                assert times[i] <= times[i + 1]
