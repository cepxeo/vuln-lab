#!/usr/bin/env bash
# Check that the services of the given profiles answer (README.md):
#
#   ./probe.sh lab-a lab-d            probe localhost
#   PROBE_HOST=10.0.0.5 ./probe.sh lab-b
#
# Each HTTP service must answer (and the middleware with its known-vulnerable
# version); Redis must answer PING without a password. Ports come from .env like
# the compose file. Exit 1 when anything does not answer.
set -uo pipefail
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
host="${PROBE_HOST:-127.0.0.1}"
failed=0

# http <name> <port> <path> [text the body must contain]
http() {
  local body status
  body="$(curl -s -L -m 20 -o - -w '\n%{http_code}' "http://$host:$2$3" 2>/dev/null)"
  status="${body##*$'\n'}"
  body="${body%$'\n'*}"
  if [ -z "$status" ] || [ "$status" = 000 ]; then
    echo "FAIL $1 http://$host:$2$3: no answer"; failed=1; return
  fi
  if [ -n "${4:-}" ] && ! grep -qF -- "$4" <<<"$body"; then
    echo "FAIL $1 http://$host:$2$3: HTTP $status without \"$4\""; failed=1; return
  fi
  echo "ok   $1 http://$host:$2$3 (HTTP $status)"
}

redis_ping() {
  local answer
  answer="$( (exec 3<>"/dev/tcp/$host/$1" && printf 'PING\r\n' >&3 && timeout 5 head -c 7 <&3) 2>/dev/null | tr -d '\r\n')"
  if [ "$answer" = "+PONG" ]; then echo "ok   cache redis://$host:$1 (PING without a password)"
  else echo "FAIL cache redis://$host:$1: no PONG"; failed=1; fi
}

[ $# -gt 0 ] || { echo "usage: $0 <profile>... (lab-a lab-b lab-c lab-d lab-e zoo-smoke zoo-all)" >&2; exit 2; }
for profile in "$@"; do
  case "$profile" in
    lab-a)
      http claimdesk "${CLAIMDESK_PORT:-8101}" /login
      http geoserver "${GEOSERVER_PORT:-8102}" /geoserver/web/ "2.23.1"
      ;;
    lab-b)
      http larder "${LARDER_PORT:-8201}" /
      http metabase "${METABASE_PORT:-8202}" /api/session/properties "v0.46.6"
      ;;
    lab-c)
      http edge "${EDGE_PORT:-8300}" /nginx_status "Active connections"
      http edge-shop "${EDGE_PORT:-8300}" /shop/
      http shopfront "${SHOPFRONT_PORT:-8301}" /
      http taskhub "${TASKHUB_PORT:-8302}" /
      http gateway "${GATEWAY_PORT:-8303}" /
      http echo "${ECHO_PORT:-8307}" /
      redis_ping "${REDIS_PORT:-8306}"
      ;;
    lab-d)
      http kestrel "${KESTREL_PORT:-8401}" / "Kestrel Courier"
      ;;
    lab-e)
      http stagehand "${STAGEHAND_PORT:-8501}" /
      http stagehand-config "${STAGEHAND_PORT:-8501}" /app-config.json "apiBase"
      ;;
    zoo-smoke)
      http zoo "${ZOO_PORT:-9100}" /
      http zoo-safe "${ZOO_SAFE_PORT:-9150}" /
      ;;
    zoo-all)
      for port in $(seq 9100 9119) $(seq 9150 9169); do http zoo "$port" /; done
      ;;
    *) echo "unknown profile $profile" >&2; exit 2 ;;
  esac
done
exit $failed
