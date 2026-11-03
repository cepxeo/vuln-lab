'use strict';
// LarderList API — a shared-pantry app. Deliberately vulnerable benchmark
// target. Synthetic data only.
const express = require('express');
const crypto = require('crypto');
const http = require('http');
const https = require('https');
const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

const app = express();
app.use(express.json());

// ---- hardcoded, weak signing key (also exposed in the bundle comments) ----
const JWT_SECRET = 'larder-dev-secret';

// ---------------------------------------------------------------- database
const db = new Database(':memory:');
db.exec(`
  CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,            -- stored in plaintext (benchmark)
    display_name TEXT,
    role TEXT DEFAULT 'member'
  );
  CREATE TABLE lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    name TEXT,
    notes TEXT,
    shared_pin TEXT
  );
  CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER,
    name TEXT,
    qty TEXT,
    note TEXT
  );
`);

// Weak seed credentials; no password policy anywhere.
const seedUsers = [
  ['admin@larder.test',  'admin123',   'Site Admin',  'admin'],
  ['chef@larder.test',   'chef2024',   'Head Chef',   'member'],
  ['demo@larder.test',   'demo1234',   'Demo User',   'member'],
  ['guest@larder.test',  'larder',     'Guest',       'member'],
];
const insUser = db.prepare('INSERT INTO users(email,password,display_name,role) VALUES (?,?,?,?)');
seedUsers.forEach(u => insUser.run(...u));

db.prepare('INSERT INTO lists(owner_id,name,notes,shared_pin) VALUES (?,?,?,?)')
  .run(1, 'Admin pantry', 'Restock paper + cleaning', '0000');
db.prepare('INSERT INTO lists(owner_id,name,notes,shared_pin) VALUES (?,?,?,?)')
  .run(2, 'Kitchen staples', 'Weekly order', '2468');
db.prepare('INSERT INTO lists(owner_id,name,notes,shared_pin) VALUES (?,?,?,?)')
  .run(3, 'Demo list', 'Try me', '1234');
db.prepare('INSERT INTO items(list_id,name,qty,note) VALUES (?,?,?,?)')
  .run(2, 'Olive oil', '2 bottles', 'cold-pressed');
db.prepare('INSERT INTO items(list_id,name,qty,note) VALUES (?,?,?,?)')
  .run(2, 'Flour', '5 kg', 'type 00');

// ------------------------------------------------------------------ tokens
function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
}
function signToken(payload) {
  const header = { alg: 'HS256', typ: 'JWT' };
  const h = b64url(JSON.stringify(header));
  const p = b64url(JSON.stringify(payload));
  const sig = b64url(crypto.createHmac('sha256', JWT_SECRET).update(h + '.' + p).digest());
  return `${h}.${p}.${sig}`;
}
// Verify trusts the header's alg: alg:"none" is accepted with no signature, so
// a forged unsigned token is honoured (JWT alg-confusion / none).
function verifyToken(token) {
  try {
    const [h, p, sig] = token.split('.');
    const header = JSON.parse(Buffer.from(h, 'base64').toString());
    const payload = JSON.parse(Buffer.from(p, 'base64').toString());
    if (header.alg === 'none') return payload;
    const expect = b64url(crypto.createHmac('sha256', JWT_SECRET).update(h + '.' + p).digest());
    if (expect === sig) return payload;
    return null;
  } catch (e) { return null; }
}
function auth(req, res, next) {
  const hdr = req.headers['authorization'] || '';
  const tok = hdr.replace(/^Bearer\s+/i, '');
  const payload = verifyToken(tok);
  if (!payload) return res.status(401).json({ error: 'unauthenticated' });
  req.user = payload;
  next();
}

// -------------------------------------------------------------------- auth
// Login builds the SQL by string concatenation (SQL injection) and accepts any
// password strength. Returns a JWT.
app.post('/api/login', (req, res) => {
  const { email, password } = req.body || {};
  const sql = `SELECT * FROM users WHERE email = '${email}' AND password = '${password}'`;
  try {
    const row = db.prepare(sql).get();
    if (!row) return res.status(401).json({ error: 'invalid credentials' });
    const token = signToken({ sub: row.id, email: row.email, role: row.role, name: row.display_name });
    res.json({ token, user: { id: row.id, email: row.email, role: row.role, name: row.display_name } });
  } catch (e) {
    res.status(500).json({ error: e.message, sql });   // verbose: echoes the SQL
  }
});

// Registration with no strength requirement; password stored in plaintext.
app.post('/api/register', (req, res) => {
  const { email, password, display_name } = req.body || {};
  try {
    const r = insUser.run(email, password, display_name || email, 'member');
    const token = signToken({ sub: r.lastInsertRowid, email, role: 'member', name: display_name || email });
    res.json({ token });
  } catch (e) { res.status(400).json({ error: e.message }); }
});

app.get('/api/me', auth, (req, res) => {
  const row = db.prepare('SELECT id,email,display_name,role FROM users WHERE id = ?').get(req.user.sub);
  res.json(row || {});
});

// Mass assignment: the whole body is written into the UPDATE, so role/is_admin
// style fields escalate privilege.
app.put('/api/profile', auth, (req, res) => {
  const allowed = ['email', 'display_name', 'password', 'role'];
  const sets = [], vals = [];
  for (const k of Object.keys(req.body || {})) {
    if (allowed.includes(k)) { sets.push(`${k} = ?`); vals.push(req.body[k]); }
  }
  if (!sets.length) return res.json({ updated: 0 });
  vals.push(req.user.sub);
  db.prepare(`UPDATE users SET ${sets.join(', ')} WHERE id = ?`).run(...vals);
  res.json({ updated: 1 });
});

// ------------------------------------------------------------------- lists
// IDOR: a list is returned by id with no owner/membership check.
app.get('/api/lists/:id', auth, (req, res) => {
  const list = db.prepare('SELECT * FROM lists WHERE id = ?').get(req.params.id);
  if (!list) return res.status(404).json({ error: 'not found' });
  const items = db.prepare('SELECT * FROM items WHERE list_id = ?').all(list.id);
  res.json({ list, items });
});

app.get('/api/lists', auth, (req, res) => {
  res.json(db.prepare('SELECT id,name,notes FROM lists WHERE owner_id = ?').all(req.user.sub));
});

// Item search: term concatenated into SQL (SQLi); note stored verbatim and
// later rendered as HTML by the React client (stored XSS).
app.get('/api/items/search', auth, (req, res) => {
  const q = req.query.q || '';
  const sql = `SELECT * FROM items WHERE name LIKE '%${q}%' OR note LIKE '%${q}%'`;
  try { res.json(db.prepare(sql).all()); }
  catch (e) { res.status(500).json({ error: e.message, sql }); }
});

app.post('/api/lists/:id/items', auth, (req, res) => {
  const { name, qty, note } = req.body || {};
  const r = db.prepare('INSERT INTO items(list_id,name,qty,note) VALUES (?,?,?,?)')
    .run(req.params.id, name, qty, note);
  res.json({ id: r.lastInsertRowid });
});

// ------------------------------------------------------------- integrations
// SSRF: fetches an operator-supplied URL with no allow-list and returns the body.
app.post('/api/import', auth, (req, res) => {
  const url = (req.body || {}).url;
  if (!url) return res.status(400).json({ error: 'url required' });
  const lib = url.startsWith('https:') ? https : http;
  lib.get(url, r => {
    let data = '';
    r.on('data', c => data += c);
    r.on('end', () => res.json({ status: r.statusCode, body: data.slice(0, 4096) }));
  }).on('error', e => res.status(502).json({ error: e.message }));
});

// Prototype pollution: user preferences deep-merged into a shared object.
const prefs = {};
function merge(dst, src) {
  for (const k in src) {
    if (k === '__proto__') { dst[k] = src[k]; }          // unsafe
    else if (src[k] && typeof src[k] === 'object') { dst[k] = merge(dst[k] || {}, src[k]); }
    else dst[k] = src[k];
  }
  return dst;
}
app.post('/api/prefs', auth, (req, res) => {
  merge(prefs, req.body || {});
  res.json({ ok: true, prefs });
});

// Path traversal: export a stored list to a file path joined without checks.
app.get('/api/export', auth, (req, res) => {
  const file = req.query.file || 'readme.txt';
  const full = path.join(__dirname, 'exports', file);
  try { res.type('text/plain').send(fs.readFileSync(full, 'utf8')); }
  catch (e) { res.status(404).json({ error: e.message }); }
});

// ---------------------------------------------------------- static + serve
app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));

const PORT = process.env.PORT || 5020;
app.listen(PORT, '0.0.0.0', () => console.log('LarderList API on ' + PORT));
