from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Cordoba")


def parse_time(time_str: str) -> int:
    """
    Parse GTFS time string (HH:MM:SS) to seconds since midnight.
    GTFS allows hours >= 24 for trips past midnight (e.g. 25:30:00).
    """
    h, m, s = map(int, time_str.split(":"))
    return h * 3600 + m * 60 + s


def get_now_seconds() -> int:
    """Current time in Córdoba as seconds since midnight."""
    now = datetime.now(TZ)
    return now.hour * 3600 + now.minute * 60 + now.second


def seconds_to_hhmm(seconds: int) -> str:
    """Convert seconds since midnight to HH:MM format."""
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"
