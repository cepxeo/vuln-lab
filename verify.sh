#!/usr/bin/env bash
# Prove the advanced labs against their ground truth (GROUND_TRUTH-r5.md):
#
#   ./verify.sh lab-d lab-e           both, on localhost
#   VERIFY_HOST=10.0.0.5 ./verify.sh lab-d
#
# For each lab it runs the reference exploit of every planted flaw and the
# attack on every decoy (lab-d/verify.py, lab-e/verify.py): a flaw must give its
# proof, a decoy must hold. Needs python3 (standard library only); ports come
# from .env like the compose file. The exploits change the lab's state (a
# password reset, uploads): restart the lab afterwards. Exit 1 when a case fails.
# Lab E's DOM XSS (E2) needs a browser; without one it is reported as "skip"
# (lab-e/verify.py says how to name one in VERIFY_BROWSER).
set -uo pipefail
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
host="${VERIFY_HOST:-127.0.0.1}"
failed=0

[ $# -gt 0 ] || { echo "usage: $0 <lab-d|lab-e>..." >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is needed" >&2; exit 1; }
for lab in "$@"; do
  case "$lab" in
    lab-d) port="${KESTREL_PORT:-8401}" ;;
    lab-e) port="${STAGEHAND_PORT:-8501}" ;;
    *) echo "unknown lab $lab (lab-d, lab-e)" >&2; exit 2 ;;
  esac
  echo "== $lab http://$host:$port"
  python3 "$lab/verify.py" "http://$host:$port" || failed=1
done
exit $failed
