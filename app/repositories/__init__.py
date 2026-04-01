import csv
import io
import os
import sqlite3
import zipfile

import httpx
import psutil

from app.core import GTFS_LOCAL_PATH, GTFS_URL
from app.models import Route, Stop, StopTime, Trip
from app.utils import parse_time


def log_memory(step):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024
    print(f"--- Memory at {step}: {mem:.2f} MB ---")


class GTFSRepository:
    """Data access layer for GTFS data using SQLite for efficient memory usage."""

    DB_PATH = "gtfs.db"

    def __init__(self):
        self.stops: dict[str, Stop] = {}  # stop_id -> stop dict (small, kept in memory)
        self.routes: dict[
            str, Route
        ] = {}  # route_id -> route dict (small, kept in memory)
        self.trips: dict[str, Trip] = {}  # trip_id -> trip dict (small, kept in memory)
        self.stop_times = _StopTimesSQLiteProxy(self.DB_PATH)  # Queries from DB
        self._trip_stop_seq = _TripStopSeqSQLiteProxy(self.DB_PATH)  # Queries from DB
        self._conn: sqlite3.Connection | None = None

    def load(self):
        """Download (if needed) and parse the GTFS zip."""
        self._ensure_gtfs_file()
        log_memory("Before GTFS Load")
        self._init_db()
        self._parse_gtfs()
        log_memory("After GTFS Load")

    def _ensure_gtfs_file(self):
        """Download GTFS file if it doesn't exist locally."""
        if not os.path.exists(GTFS_LOCAL_PATH):
            print("Downloading GTFS feed...")
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                r = client.get(GTFS_URL)
                r.raise_for_status()
            with open(GTFS_LOCAL_PATH, "wb") as f:
                f.write(r.content)
            print("Downloaded.")

    def _init_db(self):
        """Initialize SQLite database with schema."""
        # Remove old database if exists (to force reload)
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)

        self._conn = sqlite3.connect(self.DB_PATH)
        cursor = self._conn.cursor()

        # Create stop_times table
        cursor.execute("""
            CREATE TABLE stop_times (
                stop_id TEXT NOT NULL,
                trip_id TEXT NOT NULL,
                route_id TEXT NOT NULL,
                route_short_name TEXT,
                headsign TEXT,
                arrival_seconds INTEGER NOT NULL,
                arrival_time TEXT NOT NULL
            )
        """)

        # Create trip_stop_seq table
        cursor.execute("""
            CREATE TABLE trip_stop_seq (
                trip_id TEXT NOT NULL,
                stop_id TEXT NOT NULL,
                stop_sequence INTEGER NOT NULL
            )
        """)

        # Create indexes for fast queries
        cursor.execute("CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id)")
        cursor.execute(
            "CREATE INDEX idx_stop_times_arrival ON stop_times(arrival_seconds)"
        )
        cursor.execute(
            "CREATE INDEX idx_trip_stop_seq_trip_id ON trip_stop_seq(trip_id)"
        )

        self._conn.commit()

    def _parse_gtfs(self):
        """Parse all GTFS files from the zip."""
        print("Parsing GTFS feed...")
        with zipfile.ZipFile(GTFS_LOCAL_PATH) as zf:
            self._parse_stops(zf)
            self._parse_routes(zf)
            self._parse_trips(zf)
            self._parse_stop_times(zf)
        print(f"Loaded {len(self.stops)} stops, {len(self.routes)} routes.")

    def _read_csv(self, zf: zipfile.ZipFile, name: str):
        """Read a CSV file from the GTFS zip."""
        names = zf.namelist()
        match = next((n for n in names if n.endswith(name)), None)
        if not match:
            return []
        with zf.open(match) as f:
            content = f.read().decode("utf-8-sig")  # handle BOM
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)

    def _parse_stops(self, zf: zipfile.ZipFile):
        """Parse stops.txt from GTFS."""
        for row in self._read_csv(zf, "stops.txt"):
            self.stops[row["stop_id"]] = Stop(
                stop_id=row["stop_id"],
                name=row.get("stop_name", ""),
                lat=float(row.get("stop_lat", 0)),
                lon=float(row.get("stop_lon", 0)),
            )

    def _parse_routes(self, zf: zipfile.ZipFile):
        """Parse routes.txt from GTFS."""
        for row in self._read_csv(zf, "routes.txt"):
            self.routes[row["route_id"]] = Route(
                route_id=row["route_id"],
                short_name=row.get("route_short_name", ""),
                long_name=row.get("route_long_name", ""),
                type=row.get("route_type", ""),
            )

    def _parse_trips(self, zf: zipfile.ZipFile):
        """Parse trips.txt from GTFS."""
        for row in self._read_csv(zf, "trips.txt"):
            self.trips[row["trip_id"]] = Trip(
                trip_id=row["trip_id"],
                route_id=row.get("route_id", ""),
                service_id=row.get("service_id", ""),
                headsign=row.get("trip_headsign", ""),
            )

    def _parse_stop_times(self, zf: zipfile.ZipFile):
        """Parse stop_times.txt from GTFS and store in SQLite."""
        rows = self._read_csv(zf, "stop_times.txt")
        cursor = self._conn.cursor()

        # Batch insert for better performance
        batch_size = 1000
        batch = []

        for row in rows:
            stop_id = row["stop_id"]
            trip_id = row["trip_id"]
            arrival_str = row.get("arrival_time", "") or row.get("departure_time", "")
            if not arrival_str:
                continue
            try:
                arrival_seconds = parse_time(arrival_str)
            except ValueError:
                continue

            # Get trip and route info
            trip = self.trips.get(trip_id)
            route_id = trip.route_id if trip else ""
            headsign = trip.headsign if trip else ""
            route = self.routes.get(route_id)

            from app.utils import seconds_to_hhmm

            # Add stop_times record to batch
            batch.append(
                (
                    stop_id,
                    trip_id,
                    route_id,
                    route.short_name if route else "",
                    headsign,
                    arrival_seconds,
                    seconds_to_hhmm(arrival_seconds),
                )
            )

            # Insert batch if full
            if len(batch) >= batch_size:
                cursor.executemany(
                    """INSERT INTO stop_times 
                       (stop_id, trip_id, route_id, route_short_name, headsign, 
                        arrival_seconds, arrival_time)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    batch,
                )
                batch = []

            # Add trip->stop sequence record
            cursor.execute(
                """INSERT INTO trip_stop_seq (trip_id, stop_id, stop_sequence)
                   VALUES (?, ?, ?)""",
                (trip_id, stop_id, int(row.get("stop_sequence", 0))),
            )

        # Insert remaining batch
        if batch:
            cursor.executemany(
                """INSERT INTO stop_times 
                   (stop_id, trip_id, route_id, route_short_name, headsign, 
                    arrival_seconds, arrival_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                batch,
            )

        self._conn.commit()


class _StopTimesSQLiteProxy:
    """Proxy that implements dict-like interface for stop_times, querying from SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get(self, stop_id: str, default=None):
        """Get all arrival times for a stop, sorted by time."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """SELECT trip_id, route_id, route_short_name, headsign, 
                      arrival_seconds, arrival_time
               FROM stop_times
               WHERE stop_id = ?
               ORDER BY arrival_seconds""",
            (stop_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return default

        result = []
        for row in rows:
            result.append(
                StopTime(
                    trip_id=row["trip_id"],
                    route_id=row["route_id"],
                    route_short_name=row["route_short_name"],
                    headsign=row["headsign"],
                    arrival_seconds=row["arrival_seconds"],
                    arrival_time=row["arrival_time"],
                )
            )

        return result

    def __getitem__(self, key):
        """Support dict-like access."""
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __contains__(self, key):
        """Support 'in' operator."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM stop_times WHERE stop_id = ? LIMIT 1", (key,))
        result = cursor.fetchone() is not None
        conn.close()
        return result


class _TripStopSeqSQLiteProxy:
    """Proxy that implements dict-like interface for trip_stop_seq, querying from SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get(self, trip_id: str, default=None):
        """Get all stops for a trip, in order."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """SELECT stop_id, stop_sequence
               FROM trip_stop_seq
               WHERE trip_id = ?
               ORDER BY stop_sequence""",
            (trip_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return default

        result = []
        for row in rows:
            result.append(
                {
                    "stop_id": row["stop_id"],
                    "stop_sequence": row["stop_sequence"],
                }
            )

        return result

    def __getitem__(self, key):
        """Support dict-like access."""
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __contains__(self, key):
        """Support 'in' operator."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM trip_stop_seq WHERE trip_id = ? LIMIT 1", (key,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
