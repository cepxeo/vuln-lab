'use strict';
// Webhook management. A member can register a callback URL and send a test
// ping to it so they can confirm their endpoint receives events.
const express = require('express');
const http = require('http');
const https = require('https');
const requireAuth = require('../middleware/requireAuth');

const router = express.Router();
const hooks = [];

router.post('/', requireAuth, (req, res) => {
  const { url } = req.body || {};
  if (!url) return res.status(400).json({ error: 'url required' });
  hooks.push({ url, owner: req.user.sub });
  res.json({ registered: hooks.length });
});

// Send a test payload to a URL and report the status the endpoint returned.
router.post('/test', requireAuth, (req, res) => {
  const { url } = req.body || {};
  let u;
  try {
    u = new URL(url);
  } catch (e) {
    return res.status(400).json({ error: 'invalid url' });
  }
  const client = u.protocol === 'https:' ? https : http;
  const r = client.request(u, { method: 'POST', timeout: 5000 }, (upstream) => {
    let body = '';
    upstream.on('data', (c) => (body += c.toString().slice(0, 2048)));
    upstream.on('end', () =>
      res.json({ status: upstream.statusCode, bodyPreview: body.slice(0, 512) })
    );
  });
  r.on('error', (e) => res.status(502).json({ error: e.message }));
  r.end(JSON.stringify({ event: 'ping' }));
});

module.exports = router;
