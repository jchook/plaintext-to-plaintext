#!/usr/bin/env bash
# Bootstrap the Python environment, then hand server ownership to the launcher.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Install Python 3.10+ with venv support, then run ./run-local.sh again.' >&2
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10+ is required.")'
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'from importlib.metadata import version; assert int(version("cryptography").split(".")[0]) >= 41' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r poc/requirements.txt
fi
exec .venv/bin/python poc/launch.py "$@"
