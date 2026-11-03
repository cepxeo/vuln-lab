# ScanSuite AI benchmark — ground truth

Three demo applications plus a mis-configured middleware edge, built to measure
how well ScanSuite's AI SAST / DAST / pentest find **non-obvious** flaws. Every
planted vulnerability is reached through indirect, cross-file data flow or a
decoy control (a sanitizer that does not sanitize, a guard applied to the wrong
variable, an allow-list with a logic hole). None is a grep-able one-liner.

Scoring: a scanner "hits" a row if it reports a finding of the listed class at
the listed location. Count hits (recall), and count reports **not** in this list
or landing on a negative control (false positives).

## shopfront — Python / Flask  (SAST, DAST, pentest)

| # | Class (CWE) | Sink | Reached from | Why it is hidden |
|---|---|---|---|---|
| S1 | SQL injection (89) | `shop/data/catalog_repo.py` `search()` | `GET /catalog/search?q=` → `shop/catalog.py` → `shop/text.py normalize()` | `normalize()` looks like a sanitizer but strips only `;` and comment markers, not quotes |
| S2 | OS command injection (78) | `shop/media_tools.py make_thumbnail()` | `POST /media/export` (`label`) | `shlex.quote` is in the file but applied to `fmt`, not `label`; `label` sits in single quotes in a `sh -c` string |
| S3 | SSRF (918) | `shop/net/fetcher.py fetch_image()` | `GET /media/preview?url=` | Host allow-list uses a bareword `endswith`, so `*cdn.shop.local` style hosts and missing internal-IP checks slip through |
| S4 | Insecure deserialization (502) | `shop/account.py restore()` | `POST /account/session/restore` (`session`) | `pickle.loads` of a base64 blob presented as an opaque session token → RCE |
| S5 | Weak password hashing (916/327) | `shop/security.py hash_password()` | login path | unsalted MD5 |
| S6 | Hardcoded secret default (798) | `shop/config.py` `SECRET_KEY` | — | baked-in default signing key |
| S7 | CORS origin reflection + credentials (942) | `shop/middleware.py cors()` | all responses | reflects `Origin` with `Allow-Credentials: true` |
| S8 | Access-control bypass via XFF (290/639) | `shop/middleware.py admin_gate()` | `/admin*` | trusts first `X-Forwarded-For` hop, which the edge forwards from the client |

Negative controls (should **not** be flagged): `catalog_repo.get()` is
parameterized; the `sort` column in `/catalog/search` is allow-listed against a
fixed set.

## taskhub — Node / Express  (SAST, DAST, pentest)

| # | Class (CWE) | Sink | Reached from | Why it is hidden |
|---|---|---|---|---|
| T1 | JWT `alg:none` accepted (347) | `lib/auth.js readToken()` | any authenticated route | `algorithms` list includes `none`; dev-secret fallback too |
| T2 | Prototype pollution (1321) | `lib/merge.js deepMerge()` | `PATCH /settings` | recursive merge of parsed JSON with no `__proto__` guard |
| T3 | Path traversal (22) | `routes/files.js` | `GET /files/:name` | `..` guard runs **before** `decodeURIComponent`, so `%2e%2e%2f` bypasses it |
| T4 | SSRF (918) | `routes/webhooks.js` `/test` | `POST /webhooks/test` (`url`) | no allow-list, no internal-IP block, returns the upstream body |
| T5 | Reflected XSS (79) | `routes/search.js` | `GET /search?q=` | `escapeHtml` is applied to the list items but the `<h3>` header interpolates raw `q` |
| T6 | IDOR / BOLA (639) | `routes/tasks.js` `GET /:id` | `GET /tasks/:id` | list endpoint filters by owner; single-item fetch does not |
| T7 | Weak password hashing (916/327) | `lib/storage.js digest()` | login path | unsalted SHA-1 |
| T8 | CORS origin reflection + credentials (942) | `middleware/cors.js` | all responses | reflects `Origin` with credentials |

## gateway — Go  (SAST, pentest)

| # | Class (CWE) | Sink | Reached from | Why it is hidden |
|---|---|---|---|---|
| G1 | SSRF (918) | `internal/handlers/proxy.go` | `GET /proxy?target=` | fetches any caller-supplied URL via the shared client |
| G2 | OS command injection (78) | `internal/handlers/diag.go` | `GET /diag?host=` | blocklist strips `; & |` but misses `$( )`, backticks, whitespace/newline |
| G3 | Open redirect (601) | `internal/handlers/redirect.go` | `GET /go?next=` | `HasPrefix("/")` allows protocol-relative `//evil.com`; signed path uses forgeable MD5 |
| G4 | Hardcoded credentials (798) | `internal/config/config.go` | — | `InternalAPIKey`, `SigningKey` constants |
| G5 | TLS verification disabled (295) | `internal/config/config.go` | all outbound | `InsecureSkipVerify: true` on the shared client |
| G6 | Weak crypto (327) | `internal/sign/sign.go` | link signing | HMAC-MD5 |
| G7 | Non-constant-time compare (208) | `internal/sign/sign.go` `Verify()` | link verify | `==` instead of `hmac.Equal` |
| G8 | Sensitive data exposure (200) | `internal/handlers/admin.go` `AdminConfig` | `GET /admin/config` | returns the signing and internal keys; gate is a hardcoded-key check |

## middleware / infrastructure  (DAST, infra, pentest)

| # | Class (CWE) | Where | Why it is hidden |
|---|---|---|---|
| M1 | nginx alias path traversal (22) | `middleware/nginx/default.conf` `/static` | `alias` + trailing-slash mismatch → `/static../etc/passwd` |
| M2 | Status page exposed (200) | `/nginx_status` | `stub_status` reachable by anyone |
| M3 | Version disclosure (200) | `server_tokens on` | banner leaks nginx version |
| M4 | Directory listing (548) | `autoindex on` | lists the asset root |
| M5 | Unauthenticated Redis (306) | compose `cache` (6379) | no password; internal pivot target for the SSRF sinks (S3/T4/G1) |

## Exploit chains (for AI pentest)

- **XFF admin bypass → SSRF → Redis:** edge forwards client `X-Forwarded-For`
  (M-edge) → shopfront `/admin` gate trusts it (S8); SSRF sinks (S3/T4/G1) reach
  the unauthenticated Redis (M5) on the internal network.
- **JWT none → IDOR:** forge an `alg:none` admin token (T1) → read other users'
  tasks (T6) and change global settings via prototype pollution (T2).
- **Command injection → config theft:** `/gw/diag` RCE (G2) or `/media/export`
  (S2); `/admin/config` (G8) leaks keys protected only by a hardcoded value (G4).

Total planted: 8 (shopfront) + 8 (taskhub) + 8 (gateway) + 5 (middleware) = **29**.
