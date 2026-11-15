// API access. The base path is not fixed in the code: it comes from
// /app-config.json, read once at start (main.jsx).
let config = { siteName: 'Stagehand', apiBase: '/svc/v3', features: {} };

export function configure(next) {
  config = { ...config, ...next };
}

export function siteConfig() {
  return config;
}

const KEY = 'stagehand.session';

export function loadSession() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY));
  } catch (error) {
    return null;
  }
}

export function saveSession(session) {
  if (session) sessionStorage.setItem(KEY, JSON.stringify(session));
  else sessionStorage.removeItem(KEY);
  window.dispatchEvent(new Event('stagehand:session'));
}

export async function api(path, options = {}) {
  const headers = {};
  const session = loadSession();
  if (session) headers.Authorization = `Bearer ${session.token}`;
  const hasBody = options.body !== undefined;
  if (hasBody) headers['Content-Type'] = 'application/json';
  const response = await fetch(config.apiBase + path, {
    method: options.method || (hasBody ? 'POST' : 'GET'),
    headers,
    body: hasBody ? JSON.stringify(options.body) : undefined,
  });
  if (options.raw) return response;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'The request failed');
  return data;
}

export function posterUrl(eventId) {
  // Posters go through the picture proxy, which resizes and caches them.
  const source = `${window.location.origin}/posters/${eventId % 3}.svg`;
  return `${config.apiBase}/img?src=${encodeURIComponent(source)}`;
}
