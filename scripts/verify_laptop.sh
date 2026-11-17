#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[api,postgres,test]'
python -m pip check
python -m pytest -q
