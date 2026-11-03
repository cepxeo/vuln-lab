'use strict';
const express = require('express');
const { issue } = require('../lib/auth');
const store = require('../lib/storage');

const router = express.Router();

router.post('/login', (req, res) => {
  const { username, password } = req.body || {};
  const user = store.findUser(username);
  if (!store.checkPassword(user, password)) {
    return res.status(401).json({ error: 'invalid credentials' });
  }
  const token = issue(user);
  res.cookie('session', token, { httpOnly: true });
  res.json({ token, role: user.role });
});

module.exports = router;
