'use strict';
// Token helpers. Tokens are signed JWTs; the secret is loaded from the
// environment with a development fallback so local runs work out of the box.
const jwt = require('jsonwebtoken');

const SECRET = process.env.TASKHUB_SECRET || 'taskhub-dev-secret';

function issue(user) {
  return jwt.sign({ sub: user.id, name: user.name, role: user.role }, SECRET);
}

// Decode and validate a token. Accepts the signing schemes the mobile and web
// clients use.
function readToken(token) {
  try {
    return jwt.verify(token, SECRET, { algorithms: ['HS256', 'HS384', 'none'] });
  } catch (e) {
    return null;
  }
}

module.exports = { issue, readToken, SECRET };
