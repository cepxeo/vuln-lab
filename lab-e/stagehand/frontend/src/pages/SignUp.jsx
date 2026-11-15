import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, saveSession } from '../api.js';

// FNV-1a of the current invite code. The code itself is handed out by e-mail.
const INVITE_HASH = '30445ee8';

function fnv1a(text) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, '0');
}

export default function SignUp() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ invite: '', name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    setError('');
    // E11: this is the only place the invite code is checked. The register
    // endpoint accepts the request without it.
    if (fnv1a(form.invite.trim()) !== INVITE_HASH) {
      setError('This invite code is not valid.');
      return;
    }
    api('/auth/register', { body: form })
      .then((session) => { saveSession(session); navigate('/console'); })
      .catch((problem) => setError(problem.message));
  };

  return (
    <section>
      <h1>Join with an invite</h1>
      <form className="stack" onSubmit={submit}>
        <input value={form.invite} onChange={set('invite')} placeholder="Invite code" required />
        <input value={form.name} onChange={set('name')} placeholder="Name" required />
        <input type="email" value={form.email} onChange={set('email')} placeholder="E-mail" required />
        <input type="password" value={form.password} onChange={set('password')} placeholder="Password (12 characters or more)" required />
        <button type="submit">Create account</button>
        {error && <p className="error">{error}</p>}
      </form>
    </section>
  );
}
