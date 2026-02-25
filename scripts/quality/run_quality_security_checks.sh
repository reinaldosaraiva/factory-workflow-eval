#!/usr/bin/env bash
set -euo pipefail

echo "[quality] Python syntax check"
python3 -m py_compile app/*.py tests/*.py scripts/*.py

echo "[quality] Unit tests"
python3 -m unittest discover -s tests -v

echo "[security] Static secrets scan"
bash scripts/quality/scan_for_secrets.sh

echo "[quality-security] all checks passed"
