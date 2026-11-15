# vuln-lab

Intentionally vulnerable targets for benchmarking web and infrastructure
scanners (AI pentest, DAST, network): five lab stacks and a "zoo" of small
vulnerable apps with safe twins. Everything runs from one compose file, with
images published as `appsec4u/vuln-lab` on Docker Hub (public: the images hold
only the lab applications and unchanged public middleware). The ground truth of
every planted flaw is in [`ground_truth/`](ground_truth), so a scan can be
scored.

**Every service here is exploitable on purpose.** Run it only on a host you
control, reachable by the scanner and not from the internet.

## Quick start

You need Docker with the compose plugin, on Linux (Docker Engine) or macOS. On
Windows, use a WSL distribution or a Linux VM with its own Docker Engine (see
[Docker Desktop](#docker-desktop)). No login or settings are needed.

```bash
git clone https://github.com/cepxeo/vuln-lab && cd vuln-lab
./run.sh            # pulls and starts Lab A to E, waits until every service answers
```

When it is ready, `run.sh` prints the scan targets. Other commands:

```bash
./run.sh lab-c      # only some labs: lab-a to lab-e, zoo (2 targets), zoo-all (40 targets)
./run.sh zoo        # the zoo; its targets and ground truth go to zoo-out/
./run.sh status     # what runs and whether it answers
./run.sh down       # stop and remove everything
```

Defaults: the `latest` images, the ports in the table below, and, for the zoo,
this host's first network address as the address the scanner reaches. To change
any of them, copy `.env.example` to `.env` and set it there (for example,
`VULN_LAB_TAG` pins a published build).

## What is in it

| Profile | Service | Port | What it is |
|---|---|---|---|
| `lab-a` | claimdesk | 8101 | ClaimDesk, a Java/Spring Boot insurance app: SQLi, IDOR, XSS, traversal, SSTI, blind deserialization, actuator, H2 console, weak credentials |
| | geoserver | 8102 | GeoServer 2.23.1, CVE-2024-36401 (CISA KEV), app at `/geoserver` |
| `lab-b` | larder | 8201 | LarderList, React + Express |
| | metabase | 8202 | Metabase 0.46.6, CVE-2023-38646 (CISA KEV) |
| `lab-c` | edge | 8300 | mis-configured nginx 1.25 in front of the three apps |
| | shopfront | 8301 | Flask shop |
| | taskhub | 8302 | Express task board |
| | gateway | 8303 | Go asset gateway |
| | cache | 8306 | Redis 7 without a password (pivot target) |
| | echo | 8307 | false-positive trap: no planted flaw |
| `lab-d` | kestrel | 8401 | Kestrel Courier, PHP 8.3 on Apache: the advanced PHP lab (below) |
| `lab-e` | stagehand | 8501 | Stagehand, React + Express: the advanced React lab (below) |
| `zoo-smoke` | zoo | 9100, 9150 | 6 zoo apps on one origin, their safe twins on the other |
| `zoo-all` | zoo | 9100-9119, 9150-9169 | all 20 zoo apps on their own ports, twins 50 above |

What each lab plants: [GROUND_TRUTH-r4.md](GROUND_TRUTH-r4.md) (Lab A and B),
[lab-c/BENCHMARK.md](lab-c/BENCHMARK.md) and [GROUND_TRUTH-r5.md](GROUND_TRUTH-r5.md)
(Lab D and E). The machine-readable copies are in
[`ground_truth/`](ground_truth) (see [Ground truth](#ground-truth)). They name
the default ports, so keep those unless you edit the copies.

The middleware (GeoServer, Metabase, Redis, nginx) is pinned to an exact
upstream build by digest in its Dockerfile and copied to `appsec4u/vuln-lab`
unchanged. GeoServer and Metabase exist for amd64 only; on an ARM host they run
under emulation, slowly. Everything else is built for amd64 and arm64.

### The advanced labs (D and E)

Labs A and B plant textbook flaws on obvious parameters. Labs D and E are for
scanners that already find those. Each has 14 flaws and 4 decoys:

- the input is somewhere a crawler does not fuzz by default: a cookie, a path
  segment, a nested JSON field, a base64-wrapped value, a bracket-syntax query,
  a WebSocket, a GraphQL field;
- or a simple filter stops the textbook payload and a known bypass passes;
- or the proof is blind, needs a browser, or needs two steps.

Eleven flaws per lab need no account, three need one. No password is weak: the
way in is a broken sign-in process (password recovery in Lab D, an invite check
that only the page enforces in Lab E). The decoys look like the flaw and are
not; a finding on one is a false positive. Every flaw has a reference exploit:

```bash
./verify.sh lab-d lab-e     # every flaw gives its proof, every decoy holds
```

Both labs keep their state in the container and re-seed it at start. A scan
(and `verify.sh`) can reset a password or upload a file, so restart the lab
between runs: `docker compose --profile lab-d --profile lab-e up -d --force-recreate`
(a new container, so nothing a scan wrote under `/tmp` survives either).

## Run it with docker compose

`run.sh` is a wrapper around these commands; use them directly for anything it
does not cover. Without a `.env` the defaults apply (tag `latest`, the ports
above).

```bash
docker compose --profile lab-a --profile lab-b --profile lab-c pull
docker compose --profile lab-a --profile lab-b --profile lab-c up -d
./probe.sh lab-a lab-b lab-c                # every service answers, the middleware with its vulnerable version
```

The images are public, so no `docker login` is needed. Any mix of profiles
works. Stop with `docker compose --profile <...> down`. GeoServer and Metabase
take a minute or two to start.

The zoo writes its ground truth and target list for the scan. It needs the
address the scanner reaches this host at:

```bash
ZOO_ADDRESS=<address> docker compose --profile zoo-smoke up -d
cat zoo-out/targets.txt                     # the scan targets; zoo-out/zoo.yaml is the ground truth
```

### Docker Desktop

Docker Desktop's port forwarding stalled under a scanner's load (nuclei at 3-8
requests a second, two thirds of them errors), so a scan of targets published
through it measures the forwarding, not the scanner. On a Linux host (Docker
Engine) published ports are fine. On Docker Desktop:

- the zoo: start it on the host's network,
  `docker compose -f docker-compose.yml -f docker-compose.host.yml --profile zoo-smoke up -d`
  (Docker Desktop 4.34 or later, Settings > Resources > Network > Enable host networking);
- the labs: run them in a Linux VM or a WSL distribution with its own Docker
  Engine.

## Ground truth

One file per lab, [`ground_truth/<lab>.yaml`](ground_truth). The zoo writes its
own to `zoo-out/zoo.yaml` in the same form:

```yaml
stack: lab-a
services:            # service name -> ports on the lab host
  claimdesk: [8101]
items:               # planted flaws
  - id: A2
    title: SQL injection
    service: claimdesk
    classes: [sql_injection]        # the flaw's class, or cve / any
    paths: [/login, /claims/search] # optional: a finding names one of them
    cve: CVE-2024-36401             # with class cve: matched by id
    cve_aliases: [CVE-2024-36404]   # optional: other ids of the same flaw
    params: [kc_depot]              # optional: a finding names one of them (a cookie, a parameter)
    needs: [oob]                    # informative: chain, oob (out-of-band callback), poc, browser, timing
    tier: 2                         # informative, Lab D and E: 1 unusual input, 2 filter, 3 blind or chain
    pentest: false                  # source-only flaw: not expected from a dynamic scan
negatives:           # controls: any matching finding is a false positive
  - {id: N1, service: shopfront, classes: [sql_injection], paths: [/catalog/search], params: [sort]}
```

A finding hits an item when it names one of the item's classes, lands on one of
the service's ports and mentions one of its paths (when the item lists paths)
and one of its params (when it lists params).
A finding that matches a negative is a false positive.

## Building and publishing

```bash
./build.sh                    # every image for this machine, tagged <name>-<commit> and <name>-latest
./build.sh claimdesk zoo      # only some
./build.sh --check-arch       # check that our images build for amd64 and arm64 too
docker compose --profile lab-c up -d    # runs what was just built (VULN_LAB_TAG unset = latest)
./probe.sh lab-c
```

To publish (as appsec4u): commit and push first, then `docker login` and
`./build.sh --push`. It refuses uncommitted changes and a commit that is not on
`origin/main`. It builds our images for amd64 and arm64 and pushes them. It
copies the middleware digests registry to registry, byte for byte. Each image
gets two tags: `<name>-<commit>` and `<name>-latest`. Images:
`claimdesk larder shopfront taskhub gateway echo edge kestrel stagehand zoo
geoserver metabase redis`.

The zoo's apps are developed in ScanSuite's test suite. `zoo/app` is a copy of
the modules the zoo server needs, kept current with `zoo/sync.sh` in the
scansuite-teams checkout.

## Layout

```
docker-compose.yml       every service; profiles lab-a to lab-e, zoo-smoke, zoo-all
docker-compose.host.yml  the zoo on the host network (Docker Desktop)
.env.example             tag, zoo address, port overrides
run.sh                   start, stop and check the labs with the defaults (Quick start)
build.sh, probe.sh       build and publish; check that a profile answers
verify.sh                run the reference exploits of Lab D and E
ground_truth/            the planted flaws of each lab, machine-readable
GROUND_TRUTH-r4.md       Lab A and B, described
GROUND_TRUTH-r5.md       Lab D and E, described
lab-a/claimdesk          ClaimDesk source and Dockerfile
lab-a/geoserver          GeoServer 2.23.1, pinned
lab-b/larder             LarderList source and Dockerfile
lab-b/metabase           Metabase 0.46.6, pinned
lab-c/apps/*             shopfront, taskhub, gateway, echo
lab-c/edge               nginx 1.25 with the lab's config built in
lab-c/redis              Redis 7, pinned
lab-c/BENCHMARK.md       Lab C, described
lab-d/kestrel            Kestrel Courier source and Dockerfile; lab-d/verify.py
lab-e/stagehand          Stagehand source and Dockerfile; lab-e/verify.py
zoo/                     the zoo's Dockerfile and its copy of the zoo apps (app/)
```
