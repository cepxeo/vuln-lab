import React, { useState } from 'react';
import { api } from '../api.js';

export default function Tickets() {
  const [ref, setRef] = useState('');
  const [ticket, setTicket] = useState(null);
  const [layout, setLayout] = useState('classic.html');
  const [html, setHtml] = useState('');
  const [qr, setQr] = useState('');
  const [error, setError] = useState('');

  const lookup = (e) => {
    e.preventDefault();
    setError(''); setHtml(''); setQr('');
    api(`/tickets/lookup?ref=${encodeURIComponent(ref.trim())}`)
      .then((data) => setTicket(data.tickets[0]))
      .catch((problem) => { setTicket(null); setError(problem.message); });
  };

  const print = () => {
    api('/tickets/render', { body: { ticket: ticket.ref, layout: { file: layout } } })
      .then((data) => setHtml(data.html))
      .catch((problem) => setError(problem.message));
  };

  const showQr = async () => {
    const response = await api('/tickets/qr', { body: { text: ticket.ref, size: '4' }, raw: true });
    if (!response.ok) { setError('The code could not be made'); return; }
    setQr(URL.createObjectURL(await response.blob()));
  };

  return (
    <section>
      <h1>Find my ticket</h1>
      <form onSubmit={lookup}>
        <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="Ticket reference, e.g. TK-DEMO01" />
        <button type="submit">Look up</button>
      </form>
      {error && <p className="error">{error}</p>}
      {ticket && (
        <div className="card">
          <h3>{ticket.event}</h3>
          <p>Seat {ticket.seat}, ticket {ticket.ref}</p>
          <p className="small">{ticket.buyer} {ticket.note}</p>
          <select value={layout} onChange={(e) => setLayout(e.target.value)}>
            <option value="classic.html">Classic</option>
            <option value="compact.html">Compact</option>
          </select>
          <button type="button" onClick={print}>Printable ticket</button>
          <button type="button" onClick={showQr}>QR code</button>
          {html && <iframe className="ticket" title="ticket" sandbox="" srcDoc={html} />}
          {qr && <p><img src={qr} alt="QR code" style={{ width: 'auto' }} /></p>}
        </div>
      )}
    </section>
  );
}
