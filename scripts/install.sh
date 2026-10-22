#!/bin/sh
# Install RAILGUARDS into a project. Usage: scripts/install.sh [TARGET] [options]; --help for options.
set -eu

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

if command -v python3 >/dev/null 2>&1; then
  python=python3
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  python=python
else
  echo "railguards install: Python 3.9 or newer is required (the hooks run on it too)." >&2
  exit 1
fi

exec "$python" "$script_dir/install_helpers.py" "$@"
