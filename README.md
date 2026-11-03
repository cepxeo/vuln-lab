# vuln-lab: the benchmark labs and the zoo as containers

Intentionally vulnerable targets for testing ScanSuite's AI pentest, DAST and
infrastructure scanners on any machine with Docker: the three local-lab stacks
(Lab A, B, C) and the vulnerability zoo, in one compose file, published as
`appsec4u/vuln-lab` on Docker Hub (public: the images hold only the lab
applications and unchanged public middleware).

**Every service here is exploitable on purpose.** Run it only on a host you
control, reachable by the scanner and not from the internet.

## What is in it

| Profile | Service | Port | What it is |
|---|---|---|---|
| `lab-a` | claimdesk | 8101 | ClaimDesk, Java/Spring Boot insurance app: SQLi, IDOR, XSS, traversal, SSTI, blind deserialization, actuator, H2 console, weak credentials |
| | geoserver | 8102 | GeoServer 2.23.1, CVE-2024-36401 (KEV), app at `/geoserver` |
| `lab-b` | larder | 8201 | LarderList, React + Express |
| | metabase | 8202 | Metabase 0.46.6, CVE-2023-38646 (KEV) |
| `lab-c` | edge | 8300 | mis-configured nginx 1.25 in front of the three apps |
| | shopfront | 8301 | Flask shop |
| | taskhub | 8302 | Express task board |
| | gateway | 8303 | Go asset gateway |
| | cache | 8306 | Redis 7 without a password (pivot target) |
| | echo | 8307 | false-positive trap: no planted flaw |
| `zoo-smoke` | zoo | 9100, 9150 | 6 zoo apps on one origin, their safe twins on the other |
| `zoo-all` | zoo | 9100-9119, 9150-9169 | all 20 zoo apps on their own ports, twins 50 above |

What each lab plants, and how a scan is scored: [GROUND_TRUTH-r4.md](GROUND_TRUTH-r4.md)
(Lab A and B), [lab-c/BENCHMARK.md](lab-c/BENCHMARK.md), and the scoring copies in
[`tools/lab/bench/ground_truth`](../../tools/lab/bench/README.md). The ports are
the local lab's ([local-lab.md](../../docs/operations/local-lab.md)), which the
ground truth names, so keep them unless you score with edited copies.

The middleware (GeoServer, Metabase, Redis, nginx) is the exact build the local
lab runs, pinned by digest in its Dockerfile and copied to `appsec4u/vuln-lab`
unchanged. GeoServer and Metabase exist for amd64 only; on an ARM host they run
under emulation, slowly. Everything else is built for amd64 and arm64.

## On a test machine

You need Docker with the compose plugin; the images are public, so no login.

```bash
mkdir vuln-lab && cd vuln-lab
# copy docker-compose.yml, docker-compose.host.yml and .env.example from this folder
cp .env.example .env                        # set VULN_LAB_TAG to pin a build; latest is the last published
docker compose --profile lab-a --profile lab-b --profile lab-c pull
docker compose --profile lab-a --profile lab-b --profile lab-c up -d
./probe.sh lab-a lab-b lab-c                # optional: copy probe.sh too
```

Any mix of profiles works. Stop with `docker compose --profile <...> down`. GeoServer
and Metabase take a minute or two to start.

The zoo writes its ground truth and target list for the scan:

```bash
echo "ZOO_ADDRESS=<the address the scanner reaches this host at>" >> .env
docker compose --profile zoo-smoke up -d
cat zoo-out/targets.txt                     # the two smoke targets; zoo-out/zoo.yaml is the ground truth
```

Then scan and score with [`tools/zoo/smoke.py`](../../tools/zoo/README.md) from a
checkout: `--truth zoo-out/zoo.yaml --targets zoo-out/targets.txt`.

### Docker Desktop

Docker Desktop's port forwarding stalled under a scanner's load (2026-11-02:
nuclei at 3-8 requests a second, two thirds of them errors), so a scan of
targets published through it measures the forwarding, not the scanner. On a
Linux host (Docker Engine) published ports are fine. On Docker Desktop:

- the zoo: start it on the host's network,
  `docker compose -f docker-compose.yml -f docker-compose.host.yml --profile zoo-smoke up -d`
  (Docker Desktop 4.34 or later, Settings > Resources > Network > Enable host networking);
- the labs: run them in a Linux VM or WSL distribution with its own Docker
  Engine, as the local lab does (`tools/lab/deploy-target.sh`).

## Building and publishing

From a checkout, in this folder:

```bash
./build.sh                    # every image for this machine, tagged <name>-<commit> and <name>-latest
./build.sh claimdesk zoo      # only some
./build.sh --check-arch       # check that our images build for amd64 and arm64 too
docker compose --profile lab-c up -d    # runs what was just built (VULN_LAB_TAG unset = latest)
./probe.sh lab-c
```

The zoo image is built from `services/server/authorization_tests/vulnzoo`, the
code the unit suite tests (build context `services/server`), so it changes with
the zoo.

Publishing is a person's step. Commit and push to main first: `--push` refuses
uncommitted changes and a commit that is not on `origin/main`. Then:

```bash
docker login -u appsec4u
./build.sh --push
```

It builds our images for amd64 and arm64 and pushes them. It copies the
middleware digests registry to registry (`docker buildx imagetools create`),
every platform byte for byte. Each image gets two tags: `<name>-<commit>` and
`<name>-latest`. Images: `claimdesk larder shopfront taskhub gateway echo edge
zoo geoserver metabase redis`.

## Layout

```
docker-compose.yml       every service; profiles lab-a, lab-b, lab-c, zoo-smoke, zoo-all
docker-compose.host.yml  the zoo on the host network (Docker Desktop)
.env.example             tag, zoo address, port overrides
build.sh, probe.sh       build and publish; check that a profile answers
lab-a/claimdesk          ClaimDesk source and Dockerfile
lab-a/geoserver          GeoServer 2.23.1, pinned
lab-b/larder             LarderList source and Dockerfile
lab-b/metabase           Metabase 0.46.6, pinned
lab-c/apps/*             shopfront, taskhub, gateway, echo
lab-c/edge               nginx 1.25 with the lab's config built in
lab-c/redis              Redis 7, pinned
zoo/                     the zoo's Dockerfile (context services/server)
```
