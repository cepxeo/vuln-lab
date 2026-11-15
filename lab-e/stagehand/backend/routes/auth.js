'use strict';
const express = require('express');
const store = require('../lib/store');
const auth = require('../lib/auth');

const router = express.Router();

// Decoy NE2: both fields must be strings (an operator object such as
// {"$ne": null} is a 400), the lookup is a plain comparison and the password is
// checked with scrypt. No seed password is guessable.
router.post('/login', (req, res) => {
  const { email, password } = req.body || {};
  if (typeof email !== 'string' || typeof password !== 'string') return res.status(400).json({ error: 'bad request' });
  const user = store.users.find((u) => u.email === email.trim().toLowerCase());
  if (!auth.checkPassword(user, password)) return res.status(401).json({ error: 'invalid credentials' });
  res.json(auth.session(user));
});

// E11: sign-up is invite-only, but only the React form checks the invite code
// (against a hash in the bundle). This endpoint never looks at it, so a direct
// call creates a member account.
router.post('/register', (req, res) => {
  const { email, password, name } = req.body || {};
  if (typeof email !== 'string' || typeof password !== 'string') return res.status(400).json({ error: 'bad request' });
  const address = email.trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(address) || address.length > 120) return res.status(400).json({ error: 'bad e-mail address' });
  if (password.length < 12 || password.length > 200) return res.status(400).json({ error: 'the password needs 12 characters or more' });
  if (store.users.some((u) => u.email === address)) return res.status(409).json({ error: 'this address has an account' });
  const user = {
    id: store.state.nextUserId++, email: address, role: 'member',
    name: (typeof name === 'string' && name.trim() ? name.trim() : address.split('@')[0]).slice(0, 60),
    magicToken: store.randomToken(), ...store.credential(password),
  };
  store.users.push(user);
  res.status(201).json(auth.session(user));
});

// One-click sign-in with the link the console shows for a member.
router.post('/magic', (req, res) => {
  const { token } = req.body || {};
  if (typeof token !== 'string' || token.length < 12) return res.status(400).json({ error: 'bad request' });
  const user = store.users.find((u) => u.magicToken === token);
  if (!user) return res.status(401).json({ error: 'this link is not valid' });
  res.json(auth.session(user));
});

module.exports = router;
