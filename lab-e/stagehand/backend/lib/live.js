'use strict';
// Live order feed of the organizer console (WebSocket, /svc/v3/live).
const { WebSocketServer } = require('ws');
const store = require('./store');

let wss = null;

function feedView(order) {
  const buyer = store.users.find((u) => u.id === order.userId);
  return {
    order: `ORD-${order.n}`, event: store.eventTitle(order.eventId), qty: order.qty, total: order.total,
    buyer: buyer ? buyer.email : '', status: order.status, pickupCode: order.pickupCode,
  };
}

function attach(server, path) {
  wss = new WebSocketServer({ server, path, maxPayload: 4096 });
  // E9: the upgrade carries no session and none is asked for. Any client gets
  // the open pickups (buyer e-mail, pickup code) and every new order.
  wss.on('connection', (socket) => {
    const open = store.orders.filter((o) => o.status === 'awaiting pickup').map(feedView);
    socket.send(JSON.stringify({ type: 'snapshot', orders: open }));
    socket.on('error', () => {});
  });
}

function publish(order) {
  if (!wss) return;
  const message = JSON.stringify({ type: 'order', order: feedView(order) });
  for (const client of wss.clients) {
    if (client.readyState === 1) client.send(message);
  }
}

module.exports = { attach, publish };
