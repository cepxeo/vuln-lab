import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Admin({ user }) {
  const [payouts, setPayouts] = useState([]);
  const [members, setMembers] = useState([]);
  const allowed = user.role === 'admin';

  // E12: the role is checked here, in the page. The two endpoints below answer
  // any signed-in member.
  useEffect(() => {
    if (!allowed) return;
    api('/admin/payouts').then((data) => setPayouts(data.payouts)).catch(() => setPayouts([]));
    api('/admin/members').then((data) => setMembers(data.members)).catch(() => setMembers([]));
  }, [allowed]);

  if (!allowed) return <p>This area is for administrators.</p>;

  return (
    <section>
      <h1>Admin</h1>
      <h2>Payouts</h2>
      <table>
        <thead><tr><th>Id</th><th>Organizer</th><th>Amount</th><th>IBAN</th><th>Reference</th></tr></thead>
        <tbody>
          {payouts.map((row) => (
            <tr key={row.id}><td>{row.id}</td><td>{row.organizer}</td><td>{row.amount}</td><td>{row.iban}</td><td>{row.reference}</td></tr>
          ))}
        </tbody>
      </table>
      <h2>Members</h2>
      <ul>{members.map((member) => <li key={member.id}>{member.name}, {member.email} ({member.role})</li>)}</ul>
    </section>
  );
}
