import csv
import io
import logging
import os
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.stop_times: dict = {}  # stop_id -> list of arrival dicts
        self._trip_stop_seq: dict = {}  # trip_id -> list of {stop_id, stop_sequence}

    def load(self):
        """Download (if needed) and parse the GTFS zip."""
        if not os.path.exists(GTFS_LOCAL_PATH):
            logger.info("Downloading GTFS feed...")
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                r = client.get(GTFS_URL)
                r.raise_for_status()
            with open(GTFS_LOCAL_PATH, "wb") as f:
                f.write(r.content)
            logger.info("Downloaded.")

        logger.info("Parsing GTFS feed...")
        with zipfile.ZipFile(GTFS_LOCAL_PATH) as zf:
            self._parse_stops(zf)
            self._parse_routes(zf)
            self._parse_trips(zf)
            self._parse_stop_times(zf)
        logger.info(f"Loaded {len(self.stops)} stops, {len(self.routes)} routes.")

    def _read_csv(self, zf: zipfile.ZipFile, name: str):
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
        rows = self._read_csv(zf, "stop_times.txt")
        for row in rows:
            stop_id = row["stop_id"]
            trip_id = row["trip_id"]
            arrival_str = row.get("arrival_time", "") or row.get("departure_time", "")
            if not arrival_str:
                continue
            try:
                arrival_seconds = _parse_time(arrival_str)
            except ValueError:
                continue

            # Build stop_times index (for next-buses queries)
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

    def search_stops(self, query: str) -> list:
        q = query.lower()
        return [s for s in self.stops.values() if q in s["name"].lower()]

    def next_arrivals(self, stop_id: str, limit: int = 5) -> list:
        """Return the next `limit` scheduled arrivals at a stop from now."""
        now = _now_seconds()
        arrivals = self.stop_times.get(stop_id, [])

        upcoming = [a for a in arrivals if a["arrival_seconds"] >= now]
        if len(upcoming) < limit:
            upcoming += arrivals[:limit]  # wrap around midnight

        result = []
        for a in upcoming[:limit]:
            diff = a["arrival_seconds"] - now
            if diff < 0:
                diff += 86400
            result.append(
                {
                    **{k: v for k, v in a.items() if k != "arrival_seconds"},
                    "minutes_away": round(diff / 60),
                }
            )
        return result

    def stops_for_route(self, route_id: str) -> list:
        """Get ordered stops for a route (using first trip found)."""
        trip = next((t for t in self.trips.values() if t["route_id"] == route_id), None)
        if not trip:
            return []
        trip_id = trip["trip_id"]
        seq = sorted(
            self._trip_stop_seq.get(trip_id, []), key=lambda x: x["stop_sequence"]
        )
        return [self.stops[s["stop_id"]] for s in seq if s["stop_id"] in self.stops]
