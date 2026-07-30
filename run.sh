#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import ifc_compliance_mvd" 2>/dev/null; then
  .venv/bin/python -m pip install -r requirements.lock
  .venv/bin/python -m pip install -e . --no-deps
fi

exec .venv/bin/python -m ifc_compliance_mvd.cli serve
