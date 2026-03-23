# Córdoba Bus API

Static schedule API for Córdoba, Argentina urban buses.
Built with FastAPI + GTFS data from TUMI Datahub (updated Nov 2025).

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On first run, the app downloads the GTFS zip (~few MB) and parses it into memory.
Subsequent runs use the cached `gtfs.zip` file.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + stop count |
| GET | `/stops/search?q=nueva+córdoba` | Search stops by name |
| GET | `/stops/{stop_id}` | Get a stop by ID |
| GET | `/stops/{stop_id}/next-buses` | Next scheduled buses at a stop |
| GET | `/routes` | List all routes |
| GET | `/routes/{route_id}/stops` | Stops along a route |

Interactive docs available at `http://localhost:8000/docs`

## Example usage

```bash
# Find your stop
curl "http://localhost:8000/stops/search?q=colon"

# Check next buses (returns minutes_away + scheduled time)
curl "http://localhost:8000/stops/1234/next-buses?limit=5"
```

## Deploy to Render

1. Push to a GitHub repo
2. Create a new Web Service on render.com
3. Point it to the repo — `render.yaml` handles the rest

## Notes

- Times are based on **static schedules** (no realtime yet)
- Timezone: `America/Argentina/Cordoba`
- GTFS source: https://hub.tumidata.org/dataset/gtfs-cordoba
- `gtfs.zip` is downloaded once at startup and cached locally
