'use strict';
// taskhub — a small team task-board API.
//
// Routes are split by area under routes/. Cross-cutting behaviour (CORS, auth)
// lives in middleware/. Data is kept in a process-local store (lib/storage) so
// the demo needs no database.
const express = require('express');
const cookieParser = require('cookie-parser');

const cors = require('./middleware/cors');
const session = require('./routes/session');
const files = require('./routes/files');
const settings = require('./routes/settings');
const webhooks = require('./routes/webhooks');
const search = require('./routes/search');
const tasks = require('./routes/tasks');

const app = express();
app.use(express.json());
app.use(cookieParser());
app.use(cors);

app.get('/healthz', (_req, res) => res.json({ status: 'ok' }));
app.get('/', (_req, res) => {
  res.type('html').send(`<!doctype html><html><head><title>taskhub</title></head><body>
<h1>taskhub</h1>
<form action="/search" method="get">
  <input name="q" placeholder="search tasks" value="roadmap"><button>Search</button>
</form>
<ul>
  <li><a href="/search?q=roadmap">Search: roadmap</a></li>
  <li><a href="/files/notes.txt">Download notes.txt</a></li>
  <li><a href="/tasks/101">Task 101</a></li>
  <li><a href="/settings">Settings</a></li>
  <li><a href="/webhooks/test?url=http://example.com/hook">Test webhook</a></li>
</ul>
<form action="/session/login" method="post">
  <input name="username" value="alice"><input name="password" type="password"><button>Login</button>
</form>
</body></html>`);
});
app.use('/session', session);
app.use('/files', files);
app.use('/settings', settings);
app.use('/webhooks', webhooks);
app.use('/search', search);
app.use('/tasks', tasks);

const port = parseInt(process.env.PORT || '5002', 10);
app.listen(port, '0.0.0.0', () => console.log(`taskhub listening on ${port}`));
