# Known-exploitable middleware of Lab B: Metabase v0.46.6, CVE-2023-38646
# (pre-auth RCE: the setup token leaked at /api/session/properties drives
# /api/setup/validate to run an H2 JDBC payload; CISA KEV).
# The exact image the lab runs, pinned by digest (amd64 only upstream).
# build.sh --push copies this digest to appsec4u/vuln-lab unchanged.
FROM metabase/metabase:v0.46.6@sha256:e35de273692f7d95c54225abbd837a7b594e44ad42a47d8ae750293825215273
