#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest tests/ -v --cov=src/wpostgresql_mcp --cov-report=term-missing --cov-report=html:coverage_reports/htmlcov
