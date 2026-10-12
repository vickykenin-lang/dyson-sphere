#!/usr/bin/env bash
# Start every P1.10 contract stub, each on the port registry.json gives it.
# Nothing to install: the standard library is enough.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 contracts/stubs/server.py "$@"
