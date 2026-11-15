'use strict';
// Picture proxy (/svc/v3/img) and share links (/r).

const CDN_HOST = 'cdn.stagehand.test';
const PORT = process.env.PORT || 5050;

// E6: a share link may only point into the site: the target must start with
// "/" and "//" is refused. "/\host" passes, and URL parsers (browsers, fetch)
// read the backslash as a slash, so it leaves the site.
function redirect(req, res) {
  const to = typeof req.query.to === 'string' ? req.query.to : '/';
  if (!to.startsWith('/') || to.startsWith('//') || to.length > 500) return res.status(400).json({ error: 'bad target' });
  try {
    res.statusCode = 302;
    res.setHeader('Location', to);
    res.end();
  } catch (error) {
    res.status(400).json({ error: 'bad target' });
  }
}

// E7: the host of the picture must be this site's or the CDN's, and it is
// checked once. Redirects are followed without a second check, so a share link
// on this site (E6) leads the fetch to the internal key service on loopback.
async function image(req, res) {
  const src = req.query.src;
  if (typeof src !== 'string') return res.status(400).json({ error: 'src is needed' });
  let target;
  try {
    target = new URL(src);
  } catch (error) {
    return res.status(400).json({ error: 'bad src' });
  }
  if (target.protocol !== 'http:' && target.protocol !== 'https:') return res.status(400).json({ error: 'bad src' });
  const own = target.hostname === req.hostname;
  if (!own && target.hostname !== CDN_HOST) return res.status(403).json({ error: 'host not allowed' });
  // Our own pictures are read from the local listener, whatever address and
  // port the visitor used to reach the site.
  const url = own ? `http://127.0.0.1:${PORT}${target.pathname}${target.search}` : target.href;
  try {
    const upstream = await fetch(url, { redirect: 'follow', signal: AbortSignal.timeout(8000) });
    const body = Buffer.from(await upstream.arrayBuffer()).subarray(0, 512 * 1024);
    res.status(upstream.status).type(upstream.headers.get('content-type') || 'application/octet-stream').send(body);
  } catch (error) {
    res.status(502).json({ error: 'could not load the picture' });
  }
}

module.exports = { redirect, image };
