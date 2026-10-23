# Project GIVE Slicer (container)

Streamlit web app for filtering large Project GIVE / OpenCRAVAT variant CSV files into downloadable “slices” (under 50,000 variants per file).

Repository: https://github.com/MoezDawood/projectgive

## What you get

- **Slicer UI** — same behavior as `Slicer_ProjectGIVE.py`
- **Docker image** — runs on any host with Docker
- **Mounted data** — put CSVs in `./data` on the host; nothing large is baked into the image

## Requirements

- Docker Engine 20.10+ (or Docker Desktop)
- Docker Compose v2 (`docker compose`)

Optional: enough disk and RAM for multi‑GB CSVs (the app reads selected files into memory).

## Quick start (HGSC or any Linux/macOS host)

```bash
git clone https://github.com/MoezDawood/projectgive.git
cd projectgive

# Copy your annotated variant CSVs into data/ (not committed to git)
cp /path/to/your/*.csv data/

docker compose up -d --build
```

Open in a browser:

**http://localhost:8501**

(Change the host port with `SLICER_PORT=8080 docker compose up -d`.)

## Layout

| Path | Purpose |
|------|---------|
| `slicer/app.py` | Streamlit application |
| `slicer/annotatedcsvheaders.csv` | Column metadata for the filter UI |
| `data/` | **Input** variant CSVs (mounted into the container at `/data`) |
| `data/filtered_results/` | **Output** ZIP/CSV from filtering (created at runtime) |
| `state/` | Saved filter presets (`SavedSlicerFilterSet_*.json`) |

A small `data/example.csv` is included for smoke testing.

## Operations

```bash
# Logs
docker compose logs -f slicer

# Stop
docker compose down

# Rebuild after pulling updates
git pull
docker compose up -d --build
```

## Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `SLICER_DATA_DIR` | `/data` | Directory scanned for input CSVs |
| `SLICER_STATE_DIR` | `/state` | Saved filter JSON files |
| `SLICER_PORT` | `8501` | Host port mapped to the app |

## Notes for BCM-HGSC deployment

1. Clone this repo on the target machine (or pull a pre-built image if you publish one to an internal registry).
2. Mount shared storage into `data/` if CSVs live on NFS/SNFS (bind-mount the directory that holds family folders).
3. Do **not** commit patient CSVs to GitHub; only `data/example.csv` is tracked as a demo.
4. For HTTPS or SSO in front of Streamlit, put **nginx** or your cluster ingress in front of port 8501.

## License

BSD 3-Clause (see header in `slicer/app.py`).
