'use strict';
// Sessions and passwords.
//
// Decoy NE3: the session token is a JWT signed with Ed25519. The algorithm is
// pinned to EdDSA, so "alg":"none" and an HS256 token keyed with the public
// key are both refused. The key pair is made at start and never leaves the
// process (the public half is at /.well-known/jwks.json).
const crypto = require('crypto');
const store = require('./store');

const { privateKey, publicKey } = crypto.generateKeyPairSync('ed25519');
const SESSION_SECONDS = 8 * 3600;
const DUMMY = store.credential('no such account');

function encode(value) {
  return Buffer.from(JSON.stringify(value)).toString('base64url');
}

function issue(user) {
  const now = Math.floor(Date.now() / 1000);
  const head = encode({ alg: 'EdDSA', typ: 'JWT' });
  const body = encode({ sub: user.id, iat: now, exp: now + SESSION_SECONDS });
  const signature = crypto.sign(null, Buffer.from(`${head}.${body}`), privateKey).toString('base64url');
  return `${head}.${body}.${signature}`;
}

function read(token) {
  try {
    const parts = String(token).split('.');
    if (parts.length !== 3) return null;
    const header = JSON.parse(Buffer.from(parts[0], 'base64url').toString());
    if (header.alg !== 'EdDSA') return null;
    const signed = Buffer.from(`${parts[0]}.${parts[1]}`);
    if (!crypto.verify(null, signed, publicKey, Buffer.from(parts[2], 'base64url'))) return null;
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString());
    if (typeof payload.exp !== 'number' || payload.exp < Date.now() / 1000) return null;
    return payload;
  } catch (error) {
    return null;
  }
}

function checkPassword(user, password) {
  // The same work for a known and an unknown account.
  const known = user || DUMMY;
  const digest = crypto.scryptSync(password, known.salt, 32);
  return crypto.timingSafeEqual(digest, known.digest) && Boolean(user);
}

function publicUser(user) {
  return { id: user.id, email: user.email, name: user.name, role: user.role };
}

function session(user) {
  return { token: issue(user), user: publicUser(user) };
}

// The role comes from the account, never from the token.
function requireSession(req, res, next) {
  const header = req.headers.authorization || '';
  const payload = read(header.replace(/^Bearer\s+/i, ''));
  const user = payload && store.users.find((u) => u.id === payload.sub);
  if (!user) return res.status(401).json({ error: 'sign in first' });
  req.user = user;
  next();
}

function jwks() {
  return { keys: [{ ...publicKey.export({ format: 'jwk' }), use: 'sig', alg: 'EdDSA', kid: 'stagehand-1' }] };
}

module.exports = { session, checkPassword, publicUser, requireSession, jwks };
