// Auth data layer — users & sessions with GitHub repo persistence
import crypto from 'node:crypto';
import { kvGet, kvSet } from './kv.js';

const K_USERS = 'contractai:users';
const K_SESSIONS = 'contractai:sessions';

let users = [];
let sessions = {};
let usersDirty = false;
let sessionsDirty = false;

/* ============ Password hashing (scrypt + random salt) ============ */
export function hashPassword(password, salt) {
  salt = salt || crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return { salt, hash };
}

export function verifyPassword(password, salt, hash) {
  const { hash: candidate } = hashPassword(password, salt);
  const a = Buffer.from(candidate, 'hex');
  const b = Buffer.from(hash, 'hex');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

/* ============ Users ============ */
export function findUserByEmail(email) {
  return users.find(u => u.email.toLowerCase() === String(email).toLowerCase());
}

export function findUserById(id) {
  return users.find(u => u.id === id);
}

export function createUser({ email, password, display_name, org_name, role }) {
  const { salt, hash } = hashPassword(password);
  const user = {
    id: 'u_' + crypto.randomBytes(8).toString('hex'),
    email: email.toLowerCase(),
    display_name,
    org_id: 'org_' + crypto.randomBytes(4).toString('hex'),
    org_name: org_name || 'Default Org',
    role: role || 'owner',
    status: 'active',
    salt,
    hash,
    created_at: new Date().toISOString(),
  };
  users.push(user);
  usersDirty = true;
  return user;
}

export function publicUser(u) {
  if (!u) return null;
  const { salt, hash, ...rest } = u;
  return rest;
}

export function markUsersDirty() {
  usersDirty = true;
}

/* ============ Sessions ============ */
export function createSession(userId, ttlMs = 7 * 24 * 3600 * 1000) {
  const token = crypto.randomBytes(32).toString('hex');
  sessions[token] = { userId, expires: Date.now() + ttlMs };
  sessionsDirty = true;
  return token;
}

export function createRefreshToken(userId, ttlMs = 30 * 24 * 3600 * 1000) {
  const token = 'r_' + crypto.randomBytes(32).toString('hex');
  sessions[token] = { userId, expires: Date.now() + ttlMs, type: 'refresh' };
  sessionsDirty = true;
  return token;
}

export function getSession(token) {
  const s = sessions[token];
  if (!s) return null;
  if (s.expires < Date.now()) {
    delete sessions[token];
    sessionsDirty = true;
    return null;
  }
  return s;
}

export function destroySession(token) {
  if (sessions[token]) {
    delete sessions[token];
    sessionsDirty = true;
  }
}

export function authUser(req) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return null;
  const session = getSession(token);
  if (!session) return null;
  return findUserById(session.userId);
}

/* ============ Serverless lifecycle ============ */
export async function hydrate() {
  users = (await kvGet(K_USERS)) || [];
  sessions = (await kvGet(K_SESSIONS)) || {};
  // Prune expired sessions
  const now = Date.now();
  for (const t in sessions) {
    if (sessions[t].expires < now) { delete sessions[t]; sessionsDirty = true; }
  }
}

export async function persist() {
  if (usersDirty) { await kvSet(K_USERS, users); usersDirty = false; }
  if (sessionsDirty) { await kvSet(K_SESSIONS, sessions); sessionsDirty = false; }
}

export function hasUsers() {
  return users.length > 0;
}
