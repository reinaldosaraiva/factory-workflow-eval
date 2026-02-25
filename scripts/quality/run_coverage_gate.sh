#!/usr/bin/env bash
set -euo pipefail

threshold="${1:-75}"

echo "[coverage] running unit tests with coverage threshold ${threshold}%"
python3 -m coverage run --source=app -m unittest discover -s tests -v
python3 -m coverage report --fail-under "${threshold}"
echo "[coverage] gate passed"
