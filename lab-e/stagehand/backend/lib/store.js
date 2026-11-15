'use strict';
// In-memory state, rebuilt at every start. Synthetic data only.
//
// The SH-Exx-... strings are the lab's canaries: each one is reachable through
// exactly one planted flaw, so a scan's evidence can be checked (verify.py).
const crypto = require('crypto');

function credential(password) {
  const salt = crypto.randomBytes(16);
  return { salt, digest: crypto.scryptSync(password, salt, 32) };
}

function randomToken() {
  return crypto.randomBytes(18).toString('base64url');
}

// Seed accounts. The passwords are 20 random characters: none is guessable.
const users = [
  { id: 1, email: 'owner@stagehand.test', name: 'Priya Nair', role: 'admin',
    magicToken: 'SH-E05-2f9d0c64', ...credential('qT7#vL2m@Xw9Rz4!cHd6') },
  { id: 2, email: 'box.office@stagehand.test', name: 'Anders Holt', role: 'organizer',
    magicToken: randomToken(), ...credential('Jf3$Np8^bK1sYu5&gWe0') },
  { id: 3, email: 'mara.lind@buyers.test', name: 'Mara Lind', role: 'member',
    magicToken: randomToken(), ...credential('zB6!rQ9@tM2xVc7#Ln4d') },
  { id: 4, email: 'theo.katz@buyers.test', name: 'Theo Katz', role: 'member',
    magicToken: randomToken(), ...credential('Hy5&dS1*kP8wEa3^Gj7u') },
];

const events = [
  { id: 1, title: 'Harbour Lights Jazz Night', venue: 'Pier 9 Hall', date: '2027-02-14', priceFrom: 38 },
  { id: 2, title: 'Northside Comedy Cellar', venue: 'The Cellar', date: '2027-02-20', priceFrom: 22 },
  { id: 3, title: 'Glasshouse Strings', venue: 'Botanic Glasshouse', date: '2027-03-05', priceFrom: 45 },
  { id: 4, title: 'Midnight Film Marathon', venue: 'Orpheum', date: '2027-03-12', priceFrom: 18 },
  { id: 5, title: 'Riverside Food and Folk', venue: 'Mill Yard', date: '2027-04-02', priceFrom: 12 },
  { id: 6, title: 'Small Stage Open Mic', venue: 'Stagehand Loft', date: '2027-04-09', priceFrom: 8 },
];

// TK-DEMO01 is the sample the lookup page suggests.
const tickets = [
  { ref: 'TK-DEMO01', eventId: 6, buyer: 'demo@stagehand.test', seat: 'GA', note: 'Sample ticket' },
  { ref: 'TK-4A91C7', eventId: 1, buyer: 'mara.lind@buyers.test', seat: 'B12', note: '' },
  { ref: 'TK-0D3E58', eventId: 3, buyer: 'theo.katz@buyers.test', seat: 'A3', note: 'Step-free seat, call 555-0142 on arrival' },
  { ref: 'TK-9B7F21', eventId: 2, buyer: 'ines.okafor@buyers.test', seat: 'GA', note: 'Door list code SH-E04-b81e5c02' },
  { ref: 'TK-61C0AE', eventId: 4, buyer: 'jonas.reed@buyers.test', seat: 'H7', note: '' },
  { ref: 'TK-E25D90', eventId: 1, buyer: 'theo.katz@buyers.test', seat: 'B13', note: 'Gift, do not e-mail the buyer' },
];

const orders = [
  { n: 1001, userId: 3, eventId: 1, qty: 1, total: 38, status: 'awaiting pickup', pickupCode: 'PK-73104',
    billing: { name: 'Mara Lind', vatRef: '' } },
  { n: 1002, userId: 4, eventId: 3, qty: 1, total: 45, status: 'awaiting pickup', pickupCode: 'PK-20958',
    billing: { name: 'Theo Katz', vatRef: '' } },
  { n: 1003, userId: 4, eventId: 1, qty: 1, total: 38, status: 'awaiting pickup', pickupCode: 'PK-66172',
    billing: { name: 'Katz Rehearsal Rooms Ltd', vatRef: 'SH-E13-08f5b9c3' } },
  { n: 1004, userId: 3, eventId: 5, qty: 4, total: 48, status: 'awaiting pickup', pickupCode: 'PK-41830',
    billing: { name: 'Mara Lind', vatRef: '' } },
  { n: 1005, userId: 2, eventId: 2, qty: 2, total: 44, status: 'awaiting pickup', pickupCode: 'SH-E09-5a17d3e9',
    billing: { name: 'Stagehand box office', vatRef: '' } },
  { n: 1006, userId: 3, eventId: 4, qty: 2, total: 36, status: 'awaiting pickup', pickupCode: 'PK-90527',
    billing: { name: 'Mara Lind', vatRef: '' } },
];

const payouts = [
  { id: 'PO-221', organizer: 'Pier 9 Hall', amount: 4180, iban: 'DE44 5001 0517 5407 3249 31', reference: 'SH-E12-d47a0e15' },
  { id: 'PO-222', organizer: 'The Cellar', amount: 1364, iban: 'DE12 5001 0517 0648 4898 90', reference: 'CELLAR-FEB' },
  { id: 'PO-223', organizer: 'Botanic Glasshouse', amount: 2925, iban: 'DE27 1002 0890 0020 6183 34', reference: 'GLASS-0305' },
];

const reviews = {
  1: [{ author: 'Mara', html: '<p>Great room, <em>great</em> sound.</p>', at: '2026-11-02' }],
  3: [{ author: 'Theo', html: '<p>Bring a coat, the glasshouse is cold in March.</p>', at: '2026-10-21' }],
};

const state = { nextUserId: 5, nextOrder: 1007 };

function eventTitle(id) {
  const event = events.find((e) => e.id === id);
  return event ? event.title : '';
}

module.exports = { users, events, tickets, orders, payouts, reviews, state, credential, randomToken, eventTitle };
