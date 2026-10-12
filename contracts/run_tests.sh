#!/usr/bin/env bash
# Run the contract tests. By default they run against the stubs in this repository.
# To test a real component instead, point its base URL at the real one, for example:
#   DYSON_BASE_2A07=https://tool-hub.internal.example bash contracts/run_tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m unittest discover -s contracts/tests -t contracts/tests "$@"
