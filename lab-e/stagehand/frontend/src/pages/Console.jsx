import React, { useEffect, useState } from 'react';
import { api, siteConfig } from '../api.js';

const TEAM_QUERY = '{ members { id displayName role } }';

export default function Console({ user }) {
  const [orders, setOrders] = useState([]);
  const [detail, setDetail] = useState(null);
  const [team, setTeam] = useState([]);
  const [feed, setFeed] = useState([]);
  const [signature, setSignature] = useState('See you at the show,\n{{ user.name }}');
  const [preview, setPreview] = useState('');

  useEffect(() => {
    api('/orders').then((data) => setOrders(data.orders)).catch(() => setOrders([]));
    // The team list is the one GraphQL call of the console.
    api('/gql', { body: { query: TEAM_QUERY } }).then((data) => setTeam(data.data.members)).catch(() => setTeam([]));
  }, []);

  // Live orders arrive over a WebSocket next to the API.
  useEffect(() => {
    if (!siteConfig().features.liveFeed) return undefined;
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${scheme}://${window.location.host}${siteConfig().apiBase}/live`);
    socket.onmessage = (message) => {
      const data = JSON.parse(message.data);
      setFeed((current) => (data.type === 'snapshot' ? data.orders : [data.order, ...current]).slice(0, 12));
    };
    return () => socket.close();
  }, []);

  const open = (ref) => api(`/orders/${ref}`).then((data) => setDetail(data.order)).catch(() => setDetail(null));
  const render = () => api('/account/email/preview', { body: { signature } })
    .then((data) => setPreview(data.preview)).catch((problem) => setPreview(problem.message));

  return (
    <section>
      <h1>Console</h1>
      <p className="small">Signed in as {user.email} ({user.role}).</p>

      <h2>My orders</h2>
      {orders.length === 0 && <p>No orders yet.</p>}
      <ul>
        {orders.map((order) => (
          <li key={order.ref}>
            <button type="button" className="link" onClick={() => open(order.ref)}>{order.event}</button> x {order.qty}
          </li>
        ))}
      </ul>
      {detail && <p className="card">{detail.event}: {detail.qty} ticket(s), {detail.total} EUR, billed to {detail.billing.name} {detail.billing.vatRef}</p>}

      <h2>Open pickups</h2>
      <table>
        <thead><tr><th>Order</th><th>Event</th><th>Buyer</th><th>Pickup code</th></tr></thead>
        <tbody>
          {feed.map((row) => (
            <tr key={row.order}><td>{row.order}</td><td>{row.event}</td><td>{row.buyer}</td><td>{row.pickupCode}</td></tr>
          ))}
        </tbody>
      </table>

      <h2>Team</h2>
      <ul>{team.map((member) => <li key={member.id}>{member.displayName} ({member.role})</li>)}</ul>

      <h2>Ticket e-mail signature</h2>
      <div className="stack">
        <textarea rows={3} value={signature} onChange={(e) => setSignature(e.target.value)} />
        <button type="button" onClick={render}>Preview</button>
        {preview && <pre className="card">{preview}</pre>}
      </div>
    </section>
  );
}
