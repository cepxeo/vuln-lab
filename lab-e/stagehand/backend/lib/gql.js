'use strict';
// GraphQL endpoint of the organizer console (POST /svc/v3/gql).
const {
  buildSchema, parse, validate, execute, specifiedRules, NoSchemaIntrospectionCustomRule,
} = require('graphql');
const store = require('./store');

const schema = buildSchema(`
  type Event { id: ID!, title: String!, venue: String!, date: String!, priceFrom: Float! }
  type Member { id: ID!, displayName: String!, role: String!, email: String!, signInLink: String! }
  type Query {
    events: [Event!]!
    event(id: ID!): Event
    members: [Member!]!
  }
`);

const root = {
  events: () => store.events,
  event: ({ id }) => store.events.find((e) => String(e.id) === String(id)) || null,
  // E5: the member list has no session or role check. Introspection is off, but
  // the validator's "Did you mean" hints still name the fields (email,
  // signInLink), and a sign-in link is a working session for that member.
  members: () => store.users.map((u) => ({
    id: u.id, displayName: u.name, role: u.role, email: u.email,
    signInLink: `/#/signin?magic=${u.magicToken}`,
  })),
};

const RULES = [...specifiedRules, NoSchemaIntrospectionCustomRule];

async function handler(req, res) {
  const { query, variables } = req.body || {};
  if (typeof query !== 'string' || query.length > 4000) return res.status(400).json({ errors: [{ message: 'query required' }] });
  if (variables !== undefined && variables !== null && typeof variables !== 'object') {
    return res.status(400).json({ errors: [{ message: 'bad variables' }] });
  }
  let document;
  try {
    document = parse(query);
  } catch (error) {
    return res.status(400).json({ errors: [{ message: 'syntax error' }] });
  }
  const problems = validate(schema, document, RULES);
  if (problems.length) return res.status(400).json({ errors: problems.map((p) => ({ message: p.message })) });
  const result = await execute({ schema, document, rootValue: root, variableValues: variables || {} });
  const body = { data: result.data };
  if (result.errors) body.errors = result.errors.map(() => ({ message: 'request failed' }));
  res.json(body);
}

module.exports = { handler };
