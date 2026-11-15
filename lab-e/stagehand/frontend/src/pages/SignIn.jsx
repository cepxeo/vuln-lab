import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api, saveSession } from '../api.js';

export default function SignIn() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const enter = (session) => { saveSession(session); navigate('/console'); };

  // One-click links from the console: #/signin?magic=<token>
  useEffect(() => {
    const magic = params.get('magic');
    if (magic) api('/auth/magic', { body: { token: magic } }).then(enter).catch((problem) => setError(problem.message));
  }, []);

  const submit = (e) => {
    e.preventDefault();
    setError('');
    api('/auth/login', { body: { email, password } }).then(enter).catch((problem) => setError(problem.message));
  };

  return (
    <section>
      <h1>Sign in</h1>
      <form className="stack" onSubmit={submit}>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="E-mail" required />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required />
        <button type="submit">Sign in</button>
        {error && <p className="error">{error}</p>}
      </form>
      <p className="small">Organizers join by invitation. <Link to="/signup">I have an invite code</Link></p>
    </section>
  );
}
