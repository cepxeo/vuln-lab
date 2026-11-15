'use strict';
// Internal key service. It listens on the loopback address only and is never
// published: from outside it is reachable only through a request the API makes
// itself (E7).
const http = require('http');

const INTERNAL_PORT = 7001;

function listen() {
  const server = http.createServer((req, res) => {
    if (req.url === '/internal/keys') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ service: 'stagehand-internal', payoutSigningKey: 'SH-E07-e6a4317d' }));
      return;
    }
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
  });
  server.listen(INTERNAL_PORT, '127.0.0.1');
}

module.exports = { listen, INTERNAL_PORT };
