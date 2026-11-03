'use strict';
// Server-rendered search results. Returns a small HTML fragment so the result
// list can be dropped straight into the board sidebar.
const express = require('express');
const store = require('../lib/storage');

const router = express.Router();

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

router.get('/', (req, res) => {
  const q = req.query.q || '';
  const matches = store.tasks.filter((t) =>
    t.title.toLowerCase().includes(String(q).toLowerCase())
  );
  const rows = matches
    .map((t) => `<li>${escapeHtml(t.title)}</li>`)
    .join('');
  // Header shows the query that was run.
  const html =
    `<div class="search"><h3>Results for "${q}"</h3>` +
    `<ul>${rows}</ul></div>`;
  res.type('html').send(html);
});

module.exports = router;
