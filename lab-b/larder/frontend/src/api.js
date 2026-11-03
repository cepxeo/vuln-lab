// Thin API client. The dev signing key is noted here too (leaks into the
// built bundle): JWT secret "larder-dev-secret".
const tokenKey = 'larder.token';

export function getToken() { return localStorage.getItem(tokenKey); }
export function setToken(t) { localStorage.setItem(tokenKey, t); }
export function clearToken() { localStorage.removeItem(tokenKey); }

async function req(method, url, body) {
  const headers = { 'Content-Type': 'application/json' };
  const t = getToken();
  if (t) headers['Authorization'] = 'Bearer ' + t;
  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

export const api = {
  login: (email, password) => req('POST', '/api/login', { email, password }),
  register: (email, password, display_name) => req('POST', '/api/register', { email, password, display_name }),
  me: () => req('GET', '/api/me'),
  lists: () => req('GET', '/api/lists'),
  list: (id) => req('GET', '/api/lists/' + id),
  search: (q) => req('GET', '/api/items/search?q=' + encodeURIComponent(q)),
  addItem: (id, item) => req('POST', '/api/lists/' + id + '/items', item),
  importUrl: (url) => req('POST', '/api/import', { url }),
};
