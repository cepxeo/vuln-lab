#!/usr/bin/env bash
# The zoo's apps are developed in ScanSuite's test suite
# (services/server/authorization_tests/vulnzoo in the scansuite-teams repository).
# zoo/app holds a copy of the modules the zoo server needs, so this folder builds
# on its own. In the scansuite-teams checkout:
#
#   zoo/sync.sh           copy the modules here (after a change to the zoo)
#   zoo/sync.sh --check   exit 1 when the copy differs (build.sh --push runs it)
#
# The authorization suite fails too when the copy is stale
# (test_vuln_lab_zoo_copy.py).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
source_dir="$here/../../../services/server/authorization_tests/vulnzoo"
copy_dir="$here/app/authorization_tests/vulnzoo"
# serve.py and what it imports.
modules=(__init__.py serve.py server.py apps.py dast_apps.py idor_app.py)

if [ ! -d "$source_dir" ]; then
  echo "No zoo source at $source_dir: run this in the scansuite-teams checkout." >&2
  exit 2
fi

if [ "${1:-}" = "--check" ]; then
  stale=0
  for module in "${modules[@]}"; do
    cmp -s "$source_dir/$module" "$copy_dir/$module" || { echo "stale: zoo/app/authorization_tests/vulnzoo/$module" >&2; stale=1; }
  done
  [ $stale -eq 0 ] || echo "Run zoo/sync.sh and commit the copy." >&2
  exit $stale
fi

mkdir -p "$copy_dir"
for module in "${modules[@]}"; do
  cp "$source_dir/$module" "$copy_dir/$module"
done
echo "Copied ${#modules[@]} zoo modules to zoo/app."
