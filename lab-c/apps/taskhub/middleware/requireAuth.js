'use strict';
// Attach the authenticated principal to the request, or 401.
const { readToken } = require('../lib/auth');

module.exports = function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const bearer = header.startsWith('Bearer ') ? header.slice(7) : null;
  const token = bearer || req.cookies.session;
  if (!token) return res.status(401).json({ error: 'authentication required' });
  const claims = readToken(token);
  if (!claims) return res.status(401).json({ error: 'invalid token' });
  req.user = claims;
  next();
};
