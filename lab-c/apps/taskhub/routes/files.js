'use strict';
// Attachment download. Files live under a fixed root; the name is taken from
// the URL. A guard rejects path separators and parent references before the
// file is resolved.
const express = require('express');
const path = require('path');
const fs = require('fs');

const router = express.Router();
const ROOT = process.env.FILES_ROOT || '/srv/attachments';

function looksTraversal(name) {
  // Reject the obvious traversal shapes.
  return name.includes('..') || name.startsWith('/') || name.startsWith('\\');
}

router.get('/:name', (req, res) => {
  const name = req.params.name;
  if (looksTraversal(name)) {
    return res.status(400).json({ error: 'bad file name' });
  }
  // Decode percent-escapes the client used for spaces and unicode names.
  const decoded = decodeURIComponent(name);
  const full = path.join(ROOT, decoded);
  fs.readFile(full, (err, data) => {
    if (err) return res.status(404).json({ error: 'not found' });
    res.type(path.extname(full) || 'application/octet-stream').send(data);
  });
});

module.exports = router;
