// Operator directory for routing inbound SMS, email and voice to the right person.
//
// This was users.json until it acquired `process.env.X || "..."` expressions. That is not
// valid JSON, so esbuild refused to bundle it and `wrangler deploy` failed on the entry
// point — the Worker could not be built at all. A module is the honest shape for a value
// that wants an environment override.
//
// phoneToUser is derived rather than written out a second time. The JSON duplicated every
// field of every record, and its key was a computed expression, which JSON cannot express.

const users = [
  {
    username: 'chadananda',
    name: 'Chad Jones',
    phone: process.env.ADMIN_PHONE_NUMBER || '+19167656913',
    email: 'chadananda@gmail.com',
    boss_phone: process.env.ADMIN_ASSISTANT_PHONE_NUMBER || '+18447472899',
    boss_email: 'chadananda@xswarm.ai',
    role: 'admin',
    persona: 'boss',
  },
];

const phoneToUser = Object.fromEntries(users.map((u) => [u.phone, u]));

export default { users, phoneToUser };
