"""Unit tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import GTFSService
from app.repositories import GTFSRepository
from app.routes import stops, routes as routes_module


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_service(test_db_with_data, sample_stops, sample_routes, sample_trips):
    """Create a mock GTFSService with test data."""
    repo = GTFSRepository()
    repo.stops = sample_stops
    repo.routes = sample_routes
    repo.trips = sample_trips
    repo.stop_times = repo.stop_times.__class__(test_db_with_data)
    repo._trip_stop_seq = repo._trip_stop_seq.__class__(test_db_with_data)
    service = GTFSService(repo)

    # Inject the mock service into the route modules
    stops.set_service(service)
    routes_module.set_service(service)

    return service


class TestStopsEndpoints:
    """Test the /stops endpoints."""

    def test_stop_search_endpoint(self, client, mock_service):
        """Test the stop search endpoint."""
        response = client.get("/stops/search?q=centro")
        assert response.status_code == 200
        data = response.json()
        assert "stops" in data
        assert len(data["stops"]) > 0

    def test_stop_search_no_results(self, client, mock_service):
        """Test stop search with no results."""
        response = client.get("/stops/search?q=nonexistent")
        assert response.status_code == 404

    def test_get_stop_by_id(self, client, mock_service):
        """Test getting a specific stop by ID."""
        response = client.get("/stops/1001")
        assert response.status_code == 200
        data = response.json()
        assert data["stop_id"] == "1001"
        assert "name" in data
        assert "lat" in data
        assert "lon" in data

    def test_get_stop_not_found(self, client, mock_service):
        """Test getting a non-existent stop."""
        response = client.get("/stops/9999")
        assert response.status_code == 404

    def test_next_buses_endpoint(self, client, mock_service):
        """Test the next buses endpoint."""
        response = client.get("/stops/1001/next-buses")
        assert response.status_code == 200
        data = response.json()
        assert "stop" in data
        assert "next_buses" in data
        assert data["stop"]["stop_id"] == "1001"

    def test_next_buses_with_limit(self, client, mock_service):
        """Test next buses endpoint with custom limit."""
        response = client.get("/stops/1001/next-buses?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["next_buses"]) <= 2

    def test_next_buses_stop_not_found(self, client, mock_service):
        """Test next buses for non-existent stop."""
        response = client.get("/stops/9999/next-buses")
        assert response.status_code == 404

    def test_arrival_response_format(self, client, mock_service):
        """Test that arrival response has correct format."""
        response = client.get("/stops/1001/next-buses?limit=1")
        assert response.status_code == 200
        data = response.json()

        if data["next_buses"]:
            arrival = data["next_buses"][0]
            assert "trip_id" in arrival
            assert "route_id" in arrival
            assert "route_short_name" in arrival
            assert "headsign" in arrival
            assert "arrival_time" in arrival
            assert "minutes_away" in arrival


class TestRoutesEndpoints:
    """Test the /routes endpoints."""

    def test_list_routes_endpoint(self, client, mock_service):
        """Test listing all routes."""
        response = client.get("/routes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_routes_have_required_fields(self, client, mock_service):
        """Test that routes have all required fields."""
        response = client.get("/routes")
        assert response.status_code == 200
        routes = response.json()

        for route in routes:
            assert "route_id" in route
            assert "short_name" in route
            assert "long_name" in route
            assert "type" in route

    def test_get_route_stops_endpoint(self, client, mock_service):
        """Test getting stops for a specific route."""
        response = client.get("/routes/R100/stops")
        assert response.status_code == 200
        data = response.json()
        assert "route" in data
        assert "stops" in data
        assert data["route"]["route_id"] == "R100"

    def test_route_stops_in_order(self, client, mock_service):
        """Test that route stops are in correct order."""
        response = client.get("/routes/R100/stops")
        assert response.status_code == 200
        data = response.json()
        stops = data["stops"]

        # Should have stops in the correct sequence
        stop_ids = [s["stop_id"] for s in stops]
        assert stop_ids == ["1001", "1002", "1003"]

    def test_stops_have_required_fields(self, client, mock_service):
        """Test that each stop has required fields."""
        response = client.get("/routes/R100/stops")
        assert response.status_code == 200
        data = response.json()

        for stop in data["stops"]:
            assert "stop_id" in stop
            assert "name" in stop
            assert "lat" in stop
            assert "lon" in stop

    def test_get_route_not_found(self, client, mock_service):
        """Test getting stops for non-existent route."""
        response = client.get("/routes/R999/stops")
        assert response.status_code == 404


class TestResponseSchema:
    """Test that response schemas are correct."""

    def test_stop_schema(self, client, mock_service):
        """Test Stop schema in responses."""
        response = client.get("/stops/1001")
        assert response.status_code == 200
        data = response.json()

        # Verify schema
        assert isinstance(data["lat"], float)
        assert isinstance(data["lon"], float)
        assert isinstance(data["stop_id"], str)
        assert isinstance(data["name"], str)

    def test_route_schema(self, client, mock_service):
        """Test Route schema in responses."""
        response = client.get("/routes")
        assert response.status_code == 200
        routes = response.json()

        if routes:
            route = routes[0]
            assert isinstance(route["route_id"], str)
            assert isinstance(route["short_name"], str)
            assert isinstance(route["long_name"], str)
            assert isinstance(route["type"], str)

    def test_arrival_schema(self, client, mock_service):
        """Test Arrival schema in responses."""
        response = client.get("/stops/1001/next-buses?limit=1")
        assert response.status_code == 200
        data = response.json()

        if data["next_buses"]:
            arrival = data["next_buses"][0]
            assert isinstance(arrival["trip_id"], str)
            assert isinstance(arrival["route_id"], str)
            assert isinstance(arrival["route_short_name"], str)
            assert isinstance(arrival["headsign"], str)
            assert isinstance(arrival["arrival_time"], str)
            assert isinstance(arrival["minutes_away"], int)
