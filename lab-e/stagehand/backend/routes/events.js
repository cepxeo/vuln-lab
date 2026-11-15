'use strict';
const express = require('express');
const { marked } = require('marked');
const store = require('../lib/store');

const router = express.Router();

router.get('/', (req, res) => res.json({ events: store.events }));

// Decoy NE1: the term is coerced to a string and compared in memory, so
// neither SQL nor an operator object (?q[$ne]=) changes the result. The term
// comes back as JSON and the page shows it as a React text node.
router.get('/search', (req, res) => {
  const term = String(req.query.q === undefined ? '' : req.query.q).slice(0, 80);
  const needle = term.toLowerCase();
  const found = needle
    ? store.events.filter((e) => `${e.title} ${e.venue}`.toLowerCase().includes(needle))
    : [];
  res.json({ query: term, events: found });
});

function findEvent(req, res) {
  const event = store.events.find((e) => String(e.id) === req.params.id);
  if (!event) res.status(404).json({ error: 'not found' });
  return event;
}

router.get('/:id', (req, res) => {
  const event = findEvent(req, res);
  if (event) res.json({ event });
});

router.get('/:id/reviews', (req, res) => {
  const event = findEvent(req, res);
  if (event) res.json({ reviews: store.reviews[event.id] || [] });
});

// E3: a review is markdown, turned into HTML and shown with
// dangerouslySetInnerHTML. The sanitizer drops <script> blocks, javascript:
// links and event handlers written in lower case; a handler in another case
// (oNerror=) passes.
function sanitize(html) {
  return html
    .replace(/<script[\s\S]*?<\/script\s*>/gi, '')
    .replace(/<\/?script[^>]*>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/\son[a-z]+\s*=/g, ' data-removed=');
}

router.post('/:id/reviews', (req, res) => {
  const event = findEvent(req, res);
  if (!event) return;
  const { author, body } = req.body || {};
  if (typeof body !== 'string' || !body.trim() || body.length > 2000) return res.status(400).json({ error: 'a review needs some text' });
  const review = {
    author: (typeof author === 'string' && author.trim() ? author.trim() : 'Guest').slice(0, 40),
    html: sanitize(marked.parse(body, { async: false })),
    at: new Date().toISOString().slice(0, 10),
  };
  const list = store.reviews[event.id] || (store.reviews[event.id] = []);
  list.push(review);
  if (list.length > 50) list.shift();
  res.status(201).json({ review });
});

module.exports = router;
