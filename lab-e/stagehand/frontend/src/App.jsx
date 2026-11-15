import React, { Suspense, lazy, useEffect, useState } from 'react';
import { HashRouter, Link, Navigate, Route, Routes } from 'react-router-dom';
import { loadSession, saveSession } from './api.js';
import Events from './pages/Events.jsx';
import EventDetail from './pages/EventDetail.jsx';
import Tickets from './pages/Tickets.jsx';
import SignIn from './pages/SignIn.jsx';
import SignUp from './pages/SignUp.jsx';

// Signed-in screens are separate chunks, loaded on first use.
const Checkout = lazy(() => import('./pages/Checkout.jsx'));
const Console = lazy(() => import('./pages/Console.jsx'));
const Admin = lazy(() => import('./pages/Admin.jsx'));

export default function App() {
  const [session, setSession] = useState(loadSession());

  useEffect(() => {
    const refresh = () => setSession(loadSession());
    window.addEventListener('stagehand:session', refresh);
    return () => window.removeEventListener('stagehand:session', refresh);
  }, []);

  const user = session && session.user;

  return (
    <HashRouter>
      <header className="bar">
        <Link className="brand" to="/events">Stagehand</Link>
        <nav>
          <Link to="/events">Events</Link>
          <Link to="/tickets">My ticket</Link>
          {user && <Link to="/console">Console</Link>}
          {user && user.role === 'admin' && <Link to="/admin">Admin</Link>}
          {user
            ? <button type="button" className="link" onClick={() => saveSession(null)}>Sign out ({user.name})</button>
            : <Link to="/signin">Sign in</Link>}
        </nav>
      </header>
      <main>
        <Suspense fallback={<p>Loading...</p>}>
          <Routes>
            <Route path="/" element={<Navigate to="/events" replace />} />
            <Route path="/events" element={<Events />} />
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/tickets" element={<Tickets />} />
            <Route path="/signin" element={<SignIn />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/checkout/:id" element={user ? <Checkout /> : <Navigate to="/signin" replace />} />
            <Route path="/console" element={user ? <Console user={user} /> : <Navigate to="/signin" replace />} />
            <Route path="/admin" element={user ? <Admin user={user} /> : <Navigate to="/signin" replace />} />
            <Route path="*" element={<p>Page not found.</p>} />
          </Routes>
        </Suspense>
      </main>
    </HashRouter>
  );
}
