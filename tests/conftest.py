"""Pytest configuration and shared fixtures for GTFS tests."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.models import Route, Stop, Trip
from app.repositories import (
    _StopTimesSQLiteProxy,
    _TripStopSeqSQLiteProxy,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def sample_stops():
    """Create sample stop data."""
    return {
        "1001": Stop(
            stop_id="1001",
            name="Centro - Plaza San Martín",
            lat=-31.405,
            lon=-64.188,
        ),
        "1002": Stop(
            stop_id="1002",
            name="Nueva Córdoba",
            lat=-31.410,
            lon=-64.190,
        ),
        "1003": Stop(
            stop_id="1003",
            name="Barrio Güemes",
            lat=-31.395,
            lon=-64.195,
        ),
    }


@pytest.fixture
def sample_routes():
    """Create sample route data."""
    return {
        "R100": Route(
            route_id="R100",
            short_name="10",
            long_name="Centro - Cerro de las Rosas",
            type="3",
        ),
        "R200": Route(
            route_id="R200",
            short_name="20",
            long_name="Centro - San Jerónimo",
            type="3",
        ),
    }


@pytest.fixture
def sample_trips():
    """Create sample trip data."""
    return {
        "T001": Trip(
            trip_id="T001",
            route_id="R100",
            service_id="WKD",
            headsign="Towards Cerro de las Rosas",
        ),
        "T002": Trip(
            trip_id="T002",
            route_id="R100",
            service_id="WKD",
            headsign="Towards Centro",
        ),
        "T003": Trip(
            trip_id="T003",
            route_id="R200",
            service_id="WKD",
            headsign="Towards San Jerónimo",
        ),
    }


@pytest.fixture
def test_db_with_data(temp_db_path, sample_stops, sample_routes, sample_trips):
    """Create a test database with sample data."""
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute(
        """
        CREATE TABLE stop_times (
            stop_id TEXT NOT NULL,
            trip_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            route_short_name TEXT,
            headsign TEXT,
            arrival_seconds INTEGER NOT NULL,
            arrival_time TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE trip_stop_seq (
            trip_id TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            stop_sequence INTEGER NOT NULL
        )
    """
    )

    # Create indexes
    cursor.execute("CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id)")
    cursor.execute("CREATE INDEX idx_stop_times_arrival ON stop_times(arrival_seconds)")
    cursor.execute("CREATE INDEX idx_trip_stop_seq_trip_id ON trip_stop_seq(trip_id)")

    # Insert sample stop_times data
    stop_times_data = [
        ("1001", "T001", "R100", "10", "Towards Cerro", 25200, "07:00"),  # 7:00 AM
        ("1001", "T001", "R100", "10", "Towards Cerro", 28800, "08:00"),  # 8:00 AM
        ("1001", "T001", "R100", "10", "Towards Cerro", 32400, "09:00"),  # 9:00 AM
        ("1002", "T002", "R100", "10", "Towards Centro", 25200, "07:00"),
        ("1002", "T002", "R100", "10", "Towards Centro", 28800, "08:00"),
    ]

    cursor.executemany(
        """INSERT INTO stop_times 
           (stop_id, trip_id, route_id, route_short_name, headsign, arrival_seconds, arrival_time)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        stop_times_data,
    )

    # Insert trip_stop_seq data
    trip_stop_seq_data = [
        ("T001", "1001", 1),
        ("T001", "1002", 2),
        ("T001", "1003", 3),
        ("T002", "1003", 1),
        ("T002", "1002", 2),
        ("T002", "1001", 3),
        ("T003", "1001", 1),
        ("T003", "1002", 2),
    ]

    cursor.executemany(
        """INSERT INTO trip_stop_seq (trip_id, stop_id, stop_sequence)
           VALUES (?, ?, ?)""",
        trip_stop_seq_data,
    )

    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def stop_times_proxy(test_db_with_data):
    """Create a StopTimesSQLiteProxy instance."""
    return _StopTimesSQLiteProxy(test_db_with_data)


@pytest.fixture
def trip_stop_seq_proxy(test_db_with_data):
    """Create a TripStopSeqSQLiteProxy instance."""
    return _TripStopSeqSQLiteProxy(test_db_with_data)
