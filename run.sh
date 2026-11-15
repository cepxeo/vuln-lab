#!/usr/bin/env bash
# Start, stop or check the labs with no setup (README.md, "Quick start"):
#
#   ./run.sh                    pull and start Lab A to E, wait until they answer
#   ./run.sh lab-a zoo          only these: lab-a lab-b lab-c lab-d lab-e zoo (6 apps, 2 targets) zoo-all (40 targets)
#   ./run.sh down               stop and remove everything this folder started
#   ./run.sh status             what is running, and whether it answers
#
# Defaults, all overridable in .env or the environment:
#   VULN_LAB_TAG  latest (the last published build)
#   ports         8101-8102 (A), 8201-8202 (B), 8300-8307 (C), 8401 (D), 8501 (E), 9100/9150 (zoo)
#   ZOO_ADDRESS   this host's first network address (what the scanner reaches)
set -euo pipefail
cd "$(dirname "$0")"

# .env is optional; what it sets wins over the defaults below.
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export VULN_LAB_TAG="${VULN_LAB_TAG:-latest}"
ALL_PROFILES=(lab-a lab-b lab-c lab-d lab-e zoo-smoke zoo-all)
WAIT_SEC=300

# The first non-loopback address of this host.
host_address() {
  local address=""
  if command -v hostname >/dev/null 2>&1; then
    address="$(hostname -I 2>/dev/null | awk '{print $1}')" || true
  fi
  if [ -z "$address" ] && command -v ipconfig >/dev/null 2>&1; then
    address="$(ipconfig getifaddr en0 2>/dev/null || true)"   # macOS
  fi
  if [ -z "$address" ] && command -v ip >/dev/null 2>&1; then
    address="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')"
  fi
  echo "${address:-127.0.0.1}"
}

compose_profiles() {
  local args=() profile
  for profile in "$@"; do args+=(--profile "$profile"); done
  echo "${args[@]}"
}

# The ZOO_ADDRESS from the environment or .env, else this host's address.
zoo_address() {
  echo "${ZOO_ADDRESS:-$(host_address)}"
}

command -v docker >/dev/null 2>&1 || { echo "Docker is needed: https://docs.docker.com/get-docker/" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "The Docker compose plugin is needed." >&2; exit 1; }

action="up"
profiles=()
for argument in "$@"; do
  case "$argument" in
    down|stop) action="down" ;;
    status) action="status" ;;
    lab-a|lab-b|lab-c|lab-d|lab-e|zoo-all) profiles+=("$argument") ;;
    zoo|zoo-smoke) profiles+=(zoo-smoke) ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Unknown argument '$argument'. Use: lab-a lab-b lab-c lab-d lab-e zoo zoo-all, down, status." >&2; exit 2 ;;
  esac
done

case "$action" in
  down)
    # shellcheck disable=SC2046
    docker compose $(compose_profiles "${ALL_PROFILES[@]}") down -t 5
    exit 0
    ;;
  status)
    # shellcheck disable=SC2046
    docker compose $(compose_profiles "${ALL_PROFILES[@]}") ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
    # The labs whose services run (compose ps lists every container of the
    # project, whatever the profile, so map the services back to their lab).
    running=()
    # shellcheck disable=SC2046
    for service in $(docker compose $(compose_profiles "${ALL_PROFILES[@]}") ps --services --status running 2>/dev/null); do
      case "$service" in
        claimdesk|geoserver) profile=lab-a ;;
        larder|metabase) profile=lab-b ;;
        edge|shopfront|taskhub|gateway|echo|cache) profile=lab-c ;;
        kestrel) profile=lab-d ;;
        stagehand) profile=lab-e ;;
        zoo-smoke|zoo-all) profile="$service" ;;
        *) continue ;;
      esac
      case " ${running[*]} " in *" $profile "*) ;; *) running+=("$profile") ;; esac
    done
    if [ ${#running[@]} -eq 0 ]; then echo "Nothing is running. Start with: ./run.sh"; exit 0; fi
    ./probe.sh "${running[@]}"
    exit 0
    ;;
esac

[ ${#profiles[@]} -gt 0 ] || profiles=(lab-a lab-b lab-c lab-d lab-e)
for profile in "${profiles[@]}"; do
  case "$profile" in zoo-smoke|zoo-all) export ZOO_ADDRESS; ZOO_ADDRESS="$(zoo_address)" ;; esac
done

echo "Starting ${profiles[*]} (images appsec4u/vuln-lab:<name>-$VULN_LAB_TAG)."
# shellcheck disable=SC2046
docker compose $(compose_profiles "${profiles[@]}") pull --quiet
# shellcheck disable=SC2046
docker compose $(compose_profiles "${profiles[@]}") up -d --quiet-pull

echo "Waiting for the services to answer (GeoServer and Metabase take a minute or two)..."
deadline=$((SECONDS + WAIT_SEC))
until ./probe.sh "${profiles[@]}" >/tmp/vuln-lab-probe.$$ 2>&1; do
  if [ $SECONDS -ge $deadline ]; then
    cat /tmp/vuln-lab-probe.$$; rm -f /tmp/vuln-lab-probe.$$
    echo "Not every service answers after ${WAIT_SEC}s; see: docker compose logs <service>" >&2
    exit 1
  fi
  sleep 5
done
cat /tmp/vuln-lab-probe.$$; rm -f /tmp/vuln-lab-probe.$$

address="$(host_address)"
echo
echo "Ready. Scan targets (reachable as $address; ground truth in ground_truth/):"
for profile in "${profiles[@]}"; do
  case "$profile" in
    lab-a) echo "  Lab A  http://$address:${CLAIMDESK_PORT:-8101}  http://$address:${GEOSERVER_PORT:-8102}/geoserver" ;;
    lab-b) echo "  Lab B  http://$address:${LARDER_PORT:-8201}  http://$address:${METABASE_PORT:-8202}" ;;
    lab-c) echo "  Lab C  http://$address:${EDGE_PORT:-8300} (edge)  :${SHOPFRONT_PORT:-8301} :${TASKHUB_PORT:-8302} :${GATEWAY_PORT:-8303} :${ECHO_PORT:-8307}  redis :${REDIS_PORT:-8306}" ;;
    lab-d) echo "  Lab D  http://$address:${KESTREL_PORT:-8401}" ;;
    lab-e) echo "  Lab E  http://$address:${STAGEHAND_PORT:-8501}" ;;
    zoo-smoke|zoo-all) echo "  Zoo   $(tr '\n' ' ' < zoo-out/targets.txt)(ground truth: zoo-out/zoo.yaml)" ;;
  esac
done
echo "Stop with: ./run.sh down"
