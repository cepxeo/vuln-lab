import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';

// E1: the key of the ticket-mail partner belongs on the server. It is built
// into this chunk (and readable in its source map).
const TICKETMAIL_KEY = 'SH-E01-7c3a91be';

function receiptLink(order) {
  return `https://mail.stagehand.test/receipt?order=${encodeURIComponent(order.ref)}&key=${TICKETMAIL_KEY}`;
}

export default function Checkout() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [qty, setQty] = useState(1);
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api(`/events/${id}`).then((data) => setEvent(data.event)).catch(() => setEvent(null));
  }, [id]);

  const buy = (e) => {
    e.preventDefault();
    api('/orders', { body: { eventId: Number(id), qty: Number(qty) } })
      .then((data) => setOrder(data.order))
      .catch((problem) => setError(problem.message));
  };

  if (!event) return <p>Event not found.</p>;
  if (order) {
    const notice = `<b>Order confirmed.</b> ${order.qty} ticket(s) for ${event.title}.`;
    return (
      <section className="card">
        <h1>Thank you</h1>
        <p>Order {order.ref}: {order.qty} x {order.event}, {order.total} EUR.</p>
        <p><a href={receiptLink(order)}>E-mail me the receipt</a></p>
        <button type="button" onClick={() => navigate(`/events?notice=${encodeURIComponent(notice)}`)}>Back to events</button>
      </section>
    );
  }

  return (
    <section className="card">
      <h1>{event.title}</h1>
      <form className="stack" onSubmit={buy}>
        <label>Tickets <input type="number" min="1" max="8" value={qty} onChange={(e) => setQty(e.target.value)} /></label>
        <button type="submit">Pay {event.priceFrom * qty} EUR</button>
        {error && <p className="error">{error}</p>}
      </form>
    </section>
  );
}
