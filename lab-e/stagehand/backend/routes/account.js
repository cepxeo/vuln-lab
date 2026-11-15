'use strict';
// Signed-in routes of any member: profile, orders, e-mail signature.
const express = require('express');
const nunjucks = require('nunjucks');
const store = require('../lib/store');
const auth = require('../lib/auth');
const live = require('../lib/live');

const router = express.Router();

router.get('/me', auth.requireSession, (req, res) => {
  res.json({
    user: auth.publicUser(req.user),
    workspace: { name: 'Stagehand organizers', joinCode: 'SH-E11-3be8f6a0' },
  });
});

// An order's public reference is base64 of "ORD-<number>".
function orderRef(order) {
  return Buffer.from(`ORD-${order.n}`).toString('base64');
}

function orderView(order) {
  return {
    ref: orderRef(order), event: store.eventTitle(order.eventId), qty: order.qty, total: order.total,
    status: order.status, billing: order.billing,
  };
}

router.get('/orders', auth.requireSession, (req, res) => {
  res.json({ orders: store.orders.filter((o) => o.userId === req.user.id).map(orderView) });
});

router.post('/orders', auth.requireSession, (req, res) => {
  const { eventId, qty } = req.body || {};
  const event = store.events.find((e) => e.id === Number(eventId));
  const count = Number.isInteger(qty) && qty >= 1 && qty <= 8 ? qty : 1;
  if (!event) return res.status(400).json({ error: 'no such event' });
  const order = {
    n: store.state.nextOrder++, userId: req.user.id, eventId: event.id, qty: count, total: event.priceFrom * count,
    status: 'paid', pickupCode: `PK-${String(10000 + Math.floor(Math.random() * 89999))}`,
    billing: { name: req.user.name, vatRef: '' },
  };
  store.orders.push(order);
  live.publish(order);
  res.status(201).json({ order: orderView(order) });
});

// E13: the list above is filtered by owner; one order is fetched by its
// reference alone. The reference only looks opaque: decode it, change the
// number, encode it again.
router.get('/orders/:ref', auth.requireSession, (req, res) => {
  const decoded = Buffer.from(req.params.ref, 'base64').toString();
  const match = /^ORD-(\d{1,9})$/.exec(decoded);
  const order = match && store.orders.find((o) => o.n === Number(match[1]));
  if (!order) return res.status(404).json({ error: 'no such order' });
  res.json({ order: orderView(order) });
});

// E14: the signature under a member's ticket e-mails is rendered as a Nunjucks
// template, so {{7*7}} is evaluated and range.constructor reaches code execution.
const templates = new nunjucks.Environment(null, { autoescape: true });

router.post('/account/email/preview', auth.requireSession, (req, res) => {
  const { signature } = req.body || {};
  if (typeof signature !== 'string' || signature.length > 2000) return res.status(400).json({ error: 'bad signature' });
  try {
    const text = templates.renderString(`Thanks for booking with Stagehand, {{ user.name }}.\n\n${signature}`, {
      user: { name: req.user.name, email: req.user.email },
    });
    res.json({ preview: String(text).slice(0, 4000) });
  } catch (error) {
    res.status(400).json({ error: 'the signature could not be rendered' });
  }
});

module.exports = router;
