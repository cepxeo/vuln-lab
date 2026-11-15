'use strict';
// Admin screens of the console: payouts and members.
const express = require('express');
const store = require('../lib/store');
const auth = require('../lib/auth');

const router = express.Router();

// E12: the React console shows these screens to the admin role only. The API
// checks that a session exists and nothing more, so any member reads them.
router.use(auth.requireSession);

router.get('/payouts', (req, res) => res.json({ payouts: store.payouts }));

router.get('/members', (req, res) => res.json({ members: store.users.map(auth.publicUser) }));

module.exports = router;
