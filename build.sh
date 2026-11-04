#!/usr/bin/env bash
# Build the vuln-lab images (README.md); --push publishes them to appsec4u/vuln-lab.
#
#   ./build.sh                     build every image for this machine and load it
#   ./build.sh claimdesk zoo       only these (names below)
#   ./build.sh --check-arch        build our images for amd64 and arm64 without
#                                  keeping them: a check that both build
#   ./build.sh --push              publish. Our images for amd64 + arm64; the
#                                  middleware (geoserver, metabase, redis) copied
#                                  from its pinned digest unchanged, every
#                                  platform. Tags <name>-<commit> and <name>-latest.
#                                  Needs `docker login` as appsec4u, a clean tree
#                                  and a commit that is on origin/main.
#   --tag <tag>                    another tag than the commit (local builds only)
#
# Names: claimdesk larder shopfront taskhub gateway echo edge zoo (built here),
#        geoserver metabase redis (upstream, pinned in their Dockerfile).
set -euo pipefail
cd "$(dirname "$0")"

REPO=appsec4u/vuln-lab
PLATFORMS=linux/amd64,linux/arm64
BUILDER=vuln-lab

BUILT=(claimdesk larder shopfront taskhub gateway echo edge zoo)
COPIED=(geoserver metabase redis)

context_of() {
  case "$1" in
    claimdesk) echo lab-a/claimdesk ;;
    larder) echo lab-b/larder ;;
    shopfront|taskhub|gateway|echo) echo "lab-c/apps/$1" ;;
    edge) echo lab-c/edge ;;
    zoo) echo zoo ;;
    geoserver) echo lab-a/geoserver ;;
    metabase) echo lab-b/metabase ;;
    redis) echo lab-c/redis ;;
    *) return 1 ;;
  esac
}

dockerfile_of() {
  echo "$(context_of "$1")/Dockerfile"
}

# The upstream image a copied name is pinned to: its Dockerfile's FROM.
upstream_of() {
  awk '$1 == "FROM" {print $2; exit}' "$(dockerfile_of "$1")"
}

# GeoServer 2.23.1 and Metabase 0.46.6 are published for amd64 only.
local_platform_of() {
  case "$1" in
    geoserver|metabase) echo linux/amd64 ;;
    *) echo "" ;;
  esac
}

is_copied() {
  local name
  for name in "${COPIED[@]}"; do [ "$name" = "$1" ] && return 0; done
  return 1
}

mode=build
tag=""
names=()
while [ $# -gt 0 ]; do
  case "$1" in
    --push) mode=push ;;
    --check-arch) mode=check ;;
    --tag) tag="${2:?--tag needs a value}"; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    -*) echo "unknown option $1" >&2; exit 2 ;;
    *) context_of "$1" >/dev/null || { echo "unknown image $1" >&2; exit 2; }; names+=("$1") ;;
  esac
  shift
done
[ ${#names[@]} -gt 0 ] || names=("${BUILT[@]}" "${COPIED[@]}")
commit="$(git rev-parse --short=7 HEAD)"
[ -n "$tag" ] || tag="$commit"

ensure_builder() {
  docker buildx inspect "$BUILDER" >/dev/null 2>&1 || \
    docker buildx create --name "$BUILDER" --driver docker-container >/dev/null
}

if [ "$mode" = push ]; then
  [ "$tag" = "$commit" ] || { echo "--push tags the commit; drop --tag" >&2; exit 2; }
  if [ -n "$(git status --porcelain -- .)" ]; then
    echo "Uncommitted changes in this folder: commit and push them first." >&2
    exit 1
  fi
  # In the scansuite-teams checkout, the zoo copy must match the zoo it came from.
  if [ -d ../../services/server/authorization_tests/vulnzoo ]; then
    zoo/sync.sh --check
  fi
  git fetch -q origin main
  git merge-base --is-ancestor HEAD origin/main || {
    echo "HEAD ($commit) is not on origin/main: publish only what main has." >&2
    exit 1
  }
fi

labels=(--label "org.opencontainers.image.revision=$commit"
        --label "org.opencontainers.image.source=https://github.com/cepxeo/vuln-lab")

for name in "${names[@]}"; do
  context="$(context_of "$name")"
  dockerfile="$(dockerfile_of "$name")"
  case "$mode" in
    build)
      platform="$(local_platform_of "$name")"
      echo "== $name -> $REPO:$name-$tag"
      docker buildx build --load ${platform:+--platform "$platform"} "${labels[@]}" \
        -t "$REPO:$name-$tag" -t "$REPO:$name-latest" -f "$dockerfile" "$context"
      ;;
    check)
      is_copied "$name" && continue
      ensure_builder
      echo "== $name ($PLATFORMS)"
      docker buildx build --builder "$BUILDER" --platform "$PLATFORMS" -f "$dockerfile" "$context"
      ;;
    push)
      if is_copied "$name"; then
        source="$(upstream_of "$name")"
        echo "== $name: copy $source -> $REPO:$name-$tag"
        docker buildx imagetools create -t "$REPO:$name-$tag" -t "$REPO:$name-latest" "$source"
      else
        ensure_builder
        echo "== $name ($PLATFORMS) -> $REPO:$name-$tag"
        docker buildx build --builder "$BUILDER" --platform "$PLATFORMS" "${labels[@]}" --push \
          -t "$REPO:$name-$tag" -t "$REPO:$name-latest" -f "$dockerfile" "$context"
      fi
      ;;
  esac
done

if [ "$mode" = push ]; then
  echo "Published $REPO with tag $tag (and -latest). On a test machine: VULN_LAB_TAG=$tag docker compose --profile <lab> pull"
fi
