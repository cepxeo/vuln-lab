'use strict';
// Stagehand API: event tickets with an organizer console. Deliberately
// vulnerable benchmark target (vuln-lab, Lab E). Synthetic data only.
//
// The planted flaws are marked E1-E14 and the decoys NE1-NE4 where they live
// (routes/, lib/); errors are quiet on purpose: no stack traces, no query text.
const path = require('path');
const http = require('http');
const express = require('express');
const auth = require('./lib/auth');
const media = require('./routes/media');

const PORT = process.env.PORT || 5050;
const API = '/svc/v3';
const PUBLIC = path.join(__dirname, 'public');

const app = express();
app.disable('x-powered-by');
// Nested query strings (?a[b]=c) become objects; routes/tickets.js (E4).
app.set('query parser', 'extended');
app.use(express.json({ limit: '256kb' }));

// Decoy NE4: one fixed origin, never the caller's, and no credentials.
app.use(API, (req, res, next) => {
  res.set('Access-Control-Allow-Origin', 'https://stagehand.test');
  res.set('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

app.use(`${API}/auth`, require('./routes/auth'));
app.use(`${API}/events`, require('./routes/events'));
app.use(`${API}/tickets`, require('./routes/tickets'));
app.get(`${API}/img`, media.image);
app.post(`${API}/gql`, require('./lib/gql').handler);
app.use(`${API}/admin`, require('./routes/admin'));
app.use(API, require('./routes/account'));
app.use(API, (req, res) => res.status(404).json({ error: 'not found' }));

app.get('/r', media.redirect);
app.get('/.well-known/jwks.json', (req, res) => res.json(auth.jwks()));

// The React build. E1: the build's source maps (assets/*.js.map) are served
// with it, and the checkout chunk carries a partner key.
app.use(express.static(PUBLIC));
app.get('*', (req, res) => {
  if (path.extname(req.path)) return res.status(404).type('text/plain').send('Not found');
  res.sendFile(path.join(PUBLIC, 'index.html'));
});

// Quiet errors.
app.use((error, req, res, next) => { // eslint-disable-line no-unused-vars
  const status = error && error.status >= 400 && error.status < 500 ? error.status : 500;
  res.status(status).json({ error: status === 500 ? 'internal error' : 'bad request' });
});

const server = http.createServer(app);
require('./lib/live').attach(server, `${API}/live`);
server.listen(PORT, '0.0.0.0', () => console.log(`Stagehand on ${PORT}`));
require('./lib/internal').listen();
