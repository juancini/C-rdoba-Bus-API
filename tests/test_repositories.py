"""Unit tests for GTFSRepository and database functionality."""

import sqlite3

from app.repositories import GTFSRepository


class TestGTFSRepositoryDatabase:
    """Test database schema and creation."""

    def test_database_file_created(self, temp_db_path):
        """Test that database file is created."""
        from app.repositories import GTFSRepository

        repo = GTFSRepository()
        repo.DB_PATH = temp_db_path
        repo._init_db()

        # Check file exists
        import os

        assert os.path.exists(temp_db_path)

    def test_stop_times_table_schema(self, test_db_with_data):
        """Test that stop_times table has correct schema."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        # Get table info
        cursor.execute("PRAGMA table_info(stop_times)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            "stop_id": "TEXT",
            "trip_id": "TEXT",
            "route_id": "TEXT",
            "route_short_name": "TEXT",
            "headsign": "TEXT",
            "arrival_seconds": "INTEGER",
            "arrival_time": "TEXT",
        }

        for col, col_type in expected_columns.items():
            assert col in columns
            assert columns[col] == col_type

        conn.close()

    def test_trip_stop_seq_table_schema(self, test_db_with_data):
        """Test that trip_stop_seq table has correct schema."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        # Get table info
        cursor.execute("PRAGMA table_info(trip_stop_seq)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            "trip_id": "TEXT",
            "stop_id": "TEXT",
            "stop_sequence": "INTEGER",
        }

        for col, col_type in expected_columns.items():
            assert col in columns
            assert columns[col] == col_type

        conn.close()

    def test_indexes_created(self, test_db_with_data):
        """Test that database indexes are created."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        # Get list of indexes
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            "idx_stop_times_stop_id",
            "idx_stop_times_arrival",
            "idx_trip_stop_seq_trip_id",
        }

        assert expected_indexes.issubset(indexes)
        conn.close()


class TestGTFSRepositoryData:
    """Test repository data handling."""

    def test_repo_loads_stops(self, sample_stops):
        """Test that repository can store stops."""
        repo = GTFSRepository()
        repo.stops = sample_stops

        assert len(repo.stops) == 3
        assert "1001" in repo.stops

    def test_repo_loads_routes(self, sample_routes):
        """Test that repository can store routes."""
        repo = GTFSRepository()
        repo.routes = sample_routes

        assert len(repo.routes) == 2
        assert "R100" in repo.routes

    def test_repo_loads_trips(self, sample_trips):
        """Test that repository can store trips."""
        repo = GTFSRepository()
        repo.trips = sample_trips

        assert len(repo.trips) == 3
        assert "T001" in repo.trips

    def test_stop_data_structure(self, sample_stops):
        """Test that stops have correct structure."""
        stop = sample_stops["1001"]

        assert stop.stop_id == "1001"
        assert stop.name == "Centro - Plaza San Martín"
        assert isinstance(stop.lat, float)
        assert isinstance(stop.lon, float)

    def test_route_data_structure(self, sample_routes):
        """Test that routes have correct structure."""
        route = sample_routes["R100"]

        assert route.route_id == "R100"
        assert route.short_name == "10"
        assert route.long_name == "Centro - Cerro de las Rosas"
        assert route.type == "3"

    def test_trip_data_structure(self, sample_trips):
        """Test that trips have correct structure."""
        trip = sample_trips["T001"]

        assert trip.trip_id == "T001"
        assert trip.route_id == "R100"
        assert trip.service_id == "WKD"
        assert trip.headsign == "Towards Cerro de las Rosas"


class TestDatabaseQueries:
    """Test common database queries used by proxies."""

    def test_query_stop_times_by_stop_id(self, test_db_with_data):
        """Test querying stop_times by stop_id."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM stop_times WHERE stop_id = ?", ("1001",))
        count = cursor.fetchone()[0]

        assert count == 3
        conn.close()

    def test_query_trip_stop_seq_by_trip_id(self, test_db_with_data):
        """Test querying trip_stop_seq by trip_id."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM trip_stop_seq WHERE trip_id = ?", ("T001",)
        )
        count = cursor.fetchone()[0]

        assert count == 3
        conn.close()

    def test_query_ordered_by_arrival_seconds(self, test_db_with_data):
        """Test that stop_times can be ordered by arrival_seconds."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT arrival_seconds FROM stop_times WHERE stop_id = ? ORDER BY arrival_seconds",
            ("1001",),
        )
        times = [row[0] for row in cursor.fetchall()]

        # Should be sorted
        assert times == sorted(times)
        conn.close()

    def test_query_ordered_by_stop_sequence(self, test_db_with_data):
        """Test that trip_stop_seq can be ordered by stop_sequence."""
        conn = sqlite3.connect(test_db_with_data)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT stop_sequence FROM trip_stop_seq WHERE trip_id = ? ORDER BY stop_sequence",
            ("T001",),
        )
        sequences = [row[0] for row in cursor.fetchall()]

        # Should be sorted
        assert sequences == sorted(sequences)
        conn.close()
