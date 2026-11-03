'use strict';
const express = require('express');
const requireAuth = require('../middleware/requireAuth');
const store = require('../lib/storage');

const router = express.Router();

router.get('/', requireAuth, (req, res) => {
  const mine = store.tasks.filter((t) => t.owner === req.user.sub);
  res.json(mine);
});

// Fetch a single task by id.
router.get('/:id', requireAuth, (req, res) => {
  const task = store.getTask(parseInt(req.params.id, 10));
  if (!task) return res.status(404).json({ error: 'not found' });
  res.json(task);
});

module.exports = router;
