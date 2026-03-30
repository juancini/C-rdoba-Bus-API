import zipfile
import csv
import io
import os
import httpx
from app.core import GTFS_URL, GTFS_LOCAL_PATH
from app.utils import parse_time


class GTFSRepository:
    """Data access layer for GTFS data. Handles loading and parsing GTFS files."""

    def __init__(self):
        self.stops: dict = {}  # stop_id -> stop dict
        self.routes: dict = {}  # route_id -> route dict
        self.trips: dict = {}  # trip_id -> trip dict
        self.stop_times: dict = {}  # stop_id -> list of arrival dicts
        self._trip_stop_seq: dict = {}  # trip_id -> list of {stop_id, stop_sequence}

    def load(self):
        """Download (if needed) and parse the GTFS zip."""
        self._ensure_gtfs_file()
        self._parse_gtfs()

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
            self.stops[row["stop_id"]] = {
                "stop_id": row["stop_id"],
                "name": row.get("stop_name", ""),
                "lat": float(row.get("stop_lat", 0)),
                "lon": float(row.get("stop_lon", 0)),
            }

    def _parse_routes(self, zf: zipfile.ZipFile):
        """Parse routes.txt from GTFS."""
        for row in self._read_csv(zf, "routes.txt"):
            self.routes[row["route_id"]] = {
                "route_id": row["route_id"],
                "short_name": row.get("route_short_name", ""),
                "long_name": row.get("route_long_name", ""),
                "type": row.get("route_type", ""),
            }

    def _parse_trips(self, zf: zipfile.ZipFile):
        """Parse trips.txt from GTFS."""
        for row in self._read_csv(zf, "trips.txt"):
            self.trips[row["trip_id"]] = {
                "trip_id": row["trip_id"],
                "route_id": row.get("route_id", ""),
                "service_id": row.get("service_id", ""),
                "headsign": row.get("trip_headsign", ""),
            }

    def _parse_stop_times(self, zf: zipfile.ZipFile):
        """Parse stop_times.txt from GTFS."""
        rows = self._read_csv(zf, "stop_times.txt")
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

            # Build stop_times index (for next-buses queries)
            route_id = self.trips.get(trip_id, {}).get("route_id", "")
            headsign = self.trips.get(trip_id, {}).get("headsign", "")
            route = self.routes.get(route_id, {})

            if stop_id not in self.stop_times:
                self.stop_times[stop_id] = []

            from app.utils import seconds_to_hhmm

            self.stop_times[stop_id].append(
                {
                    "trip_id": trip_id,
                    "route_id": route_id,
                    "route_short_name": route.get("short_name", ""),
                    "headsign": headsign,
                    "arrival_seconds": arrival_seconds,
                    "arrival_time": seconds_to_hhmm(arrival_seconds),
                }
            )

            # Build trip->stop sequence index (for stops_for_route)
            if trip_id not in self._trip_stop_seq:
                self._trip_stop_seq[trip_id] = []
            self._trip_stop_seq[trip_id].append(
                {
                    "stop_id": stop_id,
                    "stop_sequence": int(row.get("stop_sequence", 0)),
                }
            )

        # Sort each stop's arrivals by time
        for stop_id in self.stop_times:
            self.stop_times[stop_id].sort(key=lambda x: x["arrival_seconds"])
