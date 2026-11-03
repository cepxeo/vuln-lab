'use strict';
const express = require('express');
const { deepMerge } = require('../lib/merge');
const requireAuth = require('../middleware/requireAuth');
const store = require('../lib/storage');

const router = express.Router();

router.get('/', requireAuth, (_req, res) => res.json(store.settings));

// Apply a partial settings patch. The client sends only the keys it changed.
router.patch('/', requireAuth, (req, res) => {
  const patch = req.body || {};
  deepMerge(store.settings, patch);
  res.json(store.settings);
});

module.exports = router;
