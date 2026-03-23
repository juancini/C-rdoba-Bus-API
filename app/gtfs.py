import zipfile
import csv
import io
import os
import httpx
from datetime import datetime, time
from zoneinfo import ZoneInfo

GTFS_URL = "https://s3.transitpdf.com/files/uran/improved-gtfs-cordoba-ar.zip"
GTFS_LOCAL_PATH = "gtfs.zip"
TZ = ZoneInfo("America/Argentina/Cordoba")


def _parse_time(t: str) -> int:
    """
    Parse GTFS time string (HH:MM:SS) to seconds since midnight.
    GTFS allows hours >= 24 for trips past midnight (e.g. 25:30:00).
    """
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def _now_seconds() -> int:
    """Current time in Córdoba as seconds since midnight."""
    now = datetime.now(TZ)
    return now.hour * 3600 + now.minute * 60 + now.second


def _seconds_to_hhmm(seconds: int) -> str:
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"


class GTFSData:
    def __init__(self):
        self.stops: dict = {}  # stop_id -> stop dict
        self.routes: dict = {}  # route_id -> route dict
        self.trips: dict = {}  # trip_id -> trip dict
        self.stop_times: dict = {}  # stop_id -> list of {trip_id, arrival_seconds, route_id}

    def load(self):
        """Download (if needed) and parse the GTFS zip."""
        if not os.path.exists(GTFS_LOCAL_PATH):
            print("Downloading GTFS feed...")
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                r = client.get(GTFS_URL)
                r.raise_for_status()
            with open(GTFS_LOCAL_PATH, "wb") as f:
                f.write(r.content)
            print("Downloaded.")

        print("Parsing GTFS feed...")
        with zipfile.ZipFile(GTFS_LOCAL_PATH) as zf:
            self._parse_stops(zf)
            self._parse_routes(zf)
            self._parse_trips(zf)
            self._parse_stop_times(zf)
        print(f"Loaded {len(self.stops)} stops, {len(self.routes)} routes.")

    def _read_csv(self, zf: zipfile.ZipFile, name: str):
        """Read a CSV file from the zip, return list of dicts."""
        # Some feeds put files in a subfolder
        names = zf.namelist()
        match = next((n for n in names if n.endswith(name)), None)
        if not match:
            return []
        with zf.open(match) as f:
            content = f.read().decode("utf-8-sig")  # handle BOM
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)

    def _parse_stops(self, zf):
        for row in self._read_csv(zf, "stops.txt"):
            self.stops[row["stop_id"]] = {
                "stop_id": row["stop_id"],
                "name": row.get("stop_name", ""),
                "lat": float(row.get("stop_lat", 0)),
                "lon": float(row.get("stop_lon", 0)),
            }

    def _parse_routes(self, zf):
        for row in self._read_csv(zf, "routes.txt"):
            self.routes[row["route_id"]] = {
                "route_id": row["route_id"],
                "short_name": row.get("route_short_name", ""),
                "long_name": row.get("route_long_name", ""),
                "type": row.get("route_type", ""),
            }

    def _parse_trips(self, zf):
        for row in self._read_csv(zf, "trips.txt"):
            self.trips[row["trip_id"]] = {
                "trip_id": row["trip_id"],
                "route_id": row.get("route_id", ""),
                "service_id": row.get("service_id", ""),
                "headsign": row.get("trip_headsign", ""),
            }

    def _parse_stop_times(self, zf):
        for row in self._read_csv(zf, "stop_times.txt"):
            stop_id = row["stop_id"]
            trip_id = row["trip_id"]
            arrival_str = row.get("arrival_time", "") or row.get("departure_time", "")
            if not arrival_str:
                continue
            try:
                arrival_seconds = _parse_time(arrival_str)
            except ValueError:
                continue

            route_id = self.trips.get(trip_id, {}).get("route_id", "")
            headsign = self.trips.get(trip_id, {}).get("headsign", "")
            route = self.routes.get(route_id, {})

            if stop_id not in self.stop_times:
                self.stop_times[stop_id] = []

            self.stop_times[stop_id].append(
                {
                    "trip_id": trip_id,
                    "route_id": route_id,
                    "route_short_name": route.get("short_name", ""),
                    "headsign": headsign,
                    "arrival_seconds": arrival_seconds,
                    "arrival_time": _seconds_to_hhmm(arrival_seconds),
                }
            )

        # Sort each stop's arrivals by time
        for stop_id in self.stop_times:
            self.stop_times[stop_id].sort(key=lambda x: x["arrival_seconds"])

    def search_stops(self, query: str) -> list:
        q = query.lower()
        return [s for s in self.stops.values() if q in s["name"].lower()]

    def next_arrivals(self, stop_id: str, limit: int = 5) -> list:
        """Return the next `limit` scheduled arrivals at a stop from now."""
        now = _now_seconds()
        arrivals = self.stop_times.get(stop_id, [])

        # Find upcoming arrivals (wraps around midnight)
        upcoming = [a for a in arrivals if a["arrival_seconds"] >= now]
        if len(upcoming) < limit:
            # Wrap around: add start-of-day arrivals
            upcoming += arrivals[:limit]

        result = []
        for a in upcoming[:limit]:
            diff = a["arrival_seconds"] - now
            if diff < 0:
                diff += 86400  # past midnight wrap
            result.append(
                {
                    **a,
                    "minutes_away": round(diff / 60),
                }
            )
        return result

    def stops_for_route(self, route_id: str) -> list:
        """Get ordered unique stops for a route (from first trip found)."""
        trip = next((t for t in self.trips.values() if t["route_id"] == route_id), None)
        if not trip:
            return []
        trip_id = trip["trip_id"]
        stop_ids = [
            st["stop_id"]
            for st in sorted(
                [s for s in self._flat_stop_times if s.get("trip_id") == trip_id],
                key=lambda x: x.get("stop_sequence", 0),
            )
        ]
        return [self.stops[s] for s in stop_ids if s in self.stops]
