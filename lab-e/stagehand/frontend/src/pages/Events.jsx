import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, posterUrl } from '../api.js';

export default function Events() {
  const [params] = useSearchParams();
  const [events, setEvents] = useState([]);
  const [term, setTerm] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    api('/events').then((data) => setEvents(data.events)).catch(() => setEvents([]));
  }, []);

  // E2: the notice comes from the address (#/events?notice=...) and is put into
  // the page as HTML. Only <script> blocks are stripped, so markup with an
  // event handler (<img src=x onerror=...>) runs. It never reaches the server.
  const notice = (params.get('notice') || '').replace(/<script[\s\S]*?<\/script>/gi, '');

  const search = (event) => {
    event.preventDefault();
    api(`/events/search?q=${encodeURIComponent(term)}`).then(setResult).catch(() => setResult(null));
  };

  const shown = result ? result.events : events;

  return (
    <section>
      {notice && <div className="notice" dangerouslySetInnerHTML={{ __html: notice }} />}
      <h1>Events</h1>
      <form onSubmit={search}>
        <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Search events or venues" />
        <button type="submit">Search</button>
        {result && <button type="button" onClick={() => setResult(null)}>Show all</button>}
      </form>
      {/* Decoy NE1: the term is shown as text. */}
      {result && <p>Results for "{result.query}": {result.events.length}</p>}
      <div className="grid">
        {shown.map((item) => (
          <article className="card" key={item.id}>
            <img src={posterUrl(item.id)} alt="" />
            <h3><Link to={`/events/${item.id}`}>{item.title}</Link></h3>
            <p>{item.venue}, {item.date}</p>
            <p>From {item.priceFrom} EUR</p>
          </article>
        ))}
      </div>
    </section>
  );
}
