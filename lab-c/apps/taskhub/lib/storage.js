'use strict';
// Process-local data store for the demo. Users and tasks only.
const crypto = require('crypto');

// Fast digest for the seed accounts; recomputed on every boot.
function digest(s) {
  return crypto.createHash('sha1').update(s).digest('hex');
}

const users = [
  { id: 1, name: 'alice', role: 'admin', pw: digest('correct horse') },
  { id: 2, name: 'bob', role: 'member', pw: digest('battery staple') },
];

const tasks = [
  { id: 101, owner: 1, title: 'Draft Q3 roadmap', notes: 'internal only', done: false },
  { id: 102, owner: 2, title: 'Fix login banner', notes: '', done: true },
];

const settings = { theme: 'light', perPage: 20, notify: { email: true } };

function findUser(name) {
  return users.find((u) => u.name === name);
}
function checkPassword(user, password) {
  return user && user.pw === digest(password);
}
function getTask(id) {
  return tasks.find((t) => t.id === id);
}

module.exports = { users, tasks, settings, findUser, checkPassword, getTask, digest };
