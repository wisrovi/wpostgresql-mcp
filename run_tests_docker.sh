#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim bash -c "
  pip install -e '.[dev]' && pytest tests/ -v --tb=short
"
