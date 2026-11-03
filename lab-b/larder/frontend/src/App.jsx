import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate, useParams, Navigate } from 'react-router-dom';
import { api, getToken, setToken, clearToken } from './api.js';

function Nav() {
  return (
    <div className="nav">
      <strong>LarderList</strong>
      <span>
        <Link to="/">Dashboard</Link>
        <Link to="/search">Search</Link>
        <a href="#" onClick={() => { clearToken(); location.href = '/login'; }}>Sign out</a>
      </span>
    </div>
  );
}

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const nav = useNavigate();
  const submit = async (e) => {
    e.preventDefault();
    try { const r = await api.login(email, password); setToken(r.token); nav('/'); }
    catch (e) { setErr(e.message); }
  };
  return (
    <div className="wrap">
      <form className="card auth" onSubmit={submit}>
        <h1>Sign in</h1>
        {err && <div className="err">{err}</div>}
        <label>Email</label>
        <input value={email} onChange={e => setEmail(e.target.value)} />
        <label>Password</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <button type="submit">Sign in</button>
        <p className="muted" style={{ marginTop: 12 }}><Link to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}

function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [err, setErr] = useState('');
  const nav = useNavigate();
  const submit = async (e) => {
    e.preventDefault();
    try { const r = await api.register(email, password, name); setToken(r.token); nav('/'); }
    catch (e) { setErr(e.message); }
  };
  return (
    <div className="wrap">
      <form className="card auth" onSubmit={submit}>
        <h1>Register</h1>
        {err && <div className="err">{err}</div>}
        <label>Email</label>
        <input value={email} onChange={e => setEmail(e.target.value)} />
        <label>Display name</label>
        <input value={name} onChange={e => setName(e.target.value)} />
        <label>Password</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <p className="muted">Any password length is accepted.</p>
        <button type="submit">Create account</button>
      </form>
    </div>
  );
}

function Dashboard() {
  const [lists, setLists] = useState([]);
  const [me, setMe] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    api.me().then(setMe).catch(e => setErr(e.message));
    api.lists().then(setLists).catch(e => setErr(e.message));
  }, []);
  return (
    <>
      <Nav />
      <div className="wrap">
        {err && <div className="err">{err}</div>}
        {me && <p className="muted">Signed in as {me.email} ({me.role})</p>}
        <div className="card">
          <h2>Your lists</h2>
          {lists.map(l => (
            <div className="item" key={l.id}>
              <Link to={'/list/' + l.id}>{l.name}</Link>
              {/* notes rendered as raw HTML (stored XSS) */}
              <div className="muted" dangerouslySetInnerHTML={{ __html: l.notes || '' }} />
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function ListView() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.list(id).then(setData).catch(e => setErr(e.message)); }, [id]);
  return (
    <>
      <Nav />
      <div className="wrap">
        {err && <div className="err">{err}</div>}
        {data && (
          <div className="card">
            <h2>{data.list.name}</h2>
            <div className="muted" dangerouslySetInnerHTML={{ __html: data.list.notes || '' }} />
            {data.items.map(it => (
              <div className="item" key={it.id}>
                <strong>{it.name}</strong> — {it.qty}
                {/* item note rendered as raw HTML (stored XSS) */}
                <div className="muted" dangerouslySetInnerHTML={{ __html: it.note || '' }} />
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function Search() {
  const [q, setQ] = useState('');
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState('');
  const go = async (e) => {
    e.preventDefault();
    try { setRows(await api.search(q)); setErr(''); }
    catch (e) { setErr(e.message); }
  };
  return (
    <>
      <Nav />
      <div className="wrap">
        <form className="card" onSubmit={go}>
          <h2>Search items</h2>
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="olive, flour…" />
          <button type="submit">Search</button>
          {err && <div className="err">{err}</div>}
          {rows.map(it => (
            <div className="item" key={it.id}>
              <strong>{it.name}</strong>
              <div className="muted" dangerouslySetInnerHTML={{ __html: it.note || '' }} />
            </div>
          ))}
        </form>
      </div>
    </>
  );
}

function RequireAuth({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/list/:id" element={<RequireAuth><ListView /></RequireAuth>} />
      <Route path="/search" element={<RequireAuth><Search /></RequireAuth>} />
    </Routes>
  );
}
