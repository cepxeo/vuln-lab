'use strict';
const express = require('express');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { Query } = require('mingo');
const store = require('../lib/store');

const router = express.Router();
const LAYOUTS = path.join(__dirname, '..', 'layouts');
const SAMPLE = store.tickets[0];

function view(ticket) {
  return { ref: ticket.ref, event: store.eventTitle(ticket.eventId), seat: ticket.seat, buyer: ticket.buyer, note: ticket.note };
}

// E4: the ticket reference goes into the store query as it arrives. A plain
// string matches one ticket; ?ref[$ne]=x arrives as an object (extended query
// parser) and the store reads it as an operator, so it returns other buyers'
// tickets.
router.get('/lookup', (req, res) => {
  const ref = req.query.ref;
  if (ref === undefined || ref === '') return res.status(400).json({ error: 'a ticket reference is needed' });
  let found;
  try {
    found = new Query({ ref }).find(store.tickets).all().slice(0, 25);
  } catch (error) {
    return res.status(400).json({ error: 'bad ticket reference' });
  }
  if (!found.length) return res.status(404).json({ error: 'no such ticket' });
  res.json({ tickets: found.map(view) });
});

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// E8: the layout file name is a nested JSON field. Any ".." is refused, but the
// path is built with path.resolve, so an absolute path (/etc/passwd) replaces
// the layout folder.
router.post('/render', (req, res) => {
  const body = req.body || {};
  const file = body.layout && typeof body.layout.file === 'string' ? body.layout.file : 'classic.html';
  if (file.includes('..') || file.length > 200) return res.status(400).json({ error: 'bad layout' });
  let template;
  try {
    const full = path.resolve(LAYOUTS, file);
    const stat = fs.statSync(full);
    if (!stat.isFile() || stat.size > 256 * 1024) throw new Error('not a layout');
    template = fs.readFileSync(full, 'utf8');
  } catch (error) {
    return res.status(404).json({ error: 'layout not found' });
  }
  const ticket = store.tickets.find((t) => t.ref === body.ticket) || SAMPLE;
  const fields = view(ticket);
  res.json({ html: template.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, key) => escapeHtml(fields[key] === undefined ? '' : fields[key])) });
});

function shellQuote(text) {
  return `'${String(text).replace(/'/g, `'\\''`)}'`;
}

// E10: the QR text is quoted for the shell; the module size is not. Whitespace
// and ; | & < > ` are refused, which leaves $( ) and ${IFS}. The answer is the
// image or a plain error, never the command's output (blind: timing).
const REFUSED = /[\s;|&<>`]/;

router.post('/qr', (req, res) => {
  const body = req.body || {};
  const text = typeof body.text === 'string' ? body.text.slice(0, 300) : '';
  const size = body.size === undefined ? '4' : String(body.size);
  if (!text) return res.status(400).json({ error: 'text is needed' });
  if (REFUSED.test(size) || size.length > 80) return res.status(400).json({ error: 'bad size' });
  exec(`qrencode -t PNG -s ${size} -o - -- ${shellQuote(text)}`, { encoding: 'buffer', timeout: 20000, maxBuffer: 1024 * 1024 },
    (error, stdout) => {
      if (error || !stdout.length) return res.status(500).json({ error: 'could not render the code' });
      res.type('image/png').send(stdout);
    });
});

module.exports = router;
