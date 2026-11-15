import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, posterUrl } from '../api.js';

export default function EventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [author, setAuthor] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');

  const loadReviews = () => api(`/events/${id}/reviews`).then((data) => setReviews(data.reviews)).catch(() => setReviews([]));

  useEffect(() => {
    api(`/events/${id}`).then((data) => setEvent(data.event)).catch(() => setEvent(null));
    loadReviews();
  }, [id]);

  const submit = (e) => {
    e.preventDefault();
    setError('');
    api(`/events/${id}/reviews`, { body: { author, body } })
      .then(() => { setBody(''); loadReviews(); })
      .catch((problem) => setError(problem.message));
  };

  if (!event) return <p>Event not found.</p>;
  // Share links go through /r, which only accepts targets inside the site.
  const share = `/r?to=${encodeURIComponent(`/#/events/${event.id}`)}`;

  return (
    <section>
      <div className="card">
        <img src={posterUrl(event.id)} alt="" style={{ maxWidth: 320 }} />
        <h1>{event.title}</h1>
        <p>{event.venue}, {event.date}. From {event.priceFrom} EUR.</p>
        <p><Link to={`/checkout/${event.id}`}>Buy tickets</Link> | <a href={share}>Share link</a></p>
      </div>
      <h2>Reviews</h2>
      {reviews.length === 0 && <p>No reviews yet.</p>}
      {reviews.map((review, index) => (
        <article className="card" key={index}>
          <strong>{review.author}</strong> <span className="small">{review.at}</span>
          {/* E3: the sanitized markdown from the server is trusted as HTML. */}
          <div dangerouslySetInnerHTML={{ __html: review.html }} />
        </article>
      ))}
      <h3>Write a review</h3>
      <form className="stack" onSubmit={submit}>
        <input value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="Your name" />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} placeholder="Markdown is fine" />
        <button type="submit">Post review</button>
        {error && <p className="error">{error}</p>}
      </form>
    </section>
  );
}
