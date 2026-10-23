#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p data state

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine or Docker Desktop." >&2
  exit 1
fi

docker compose up -d --build
echo "Slicer is starting. Open http://localhost:${SLICER_PORT:-8501}"
