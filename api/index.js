// Vercel Functions entry — ContractAI serverless auth API
// Routes: vercel.json rewrites /api/* → this function, req.url preserves original path
import {
  hydrate, persist, hasUsers,
  findUserByEmail, createUser, publicUser,
  createSession, createRefreshToken, getSession, destroySession,
  verifyPassword, hashPassword, authUser, findUserById, markUsersDirty,
} from './auth.js';

export const config = {
  api: { bodyParser: false, externalResolver: true },
};

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString() || '{}')); }
      catch { resolve({}); }
    });
    req.on('error', reject);
  });
}

function json(res, status, data) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  });
  res.end(JSON.stringify(data));
}

export default async function handler(req, res) {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Authorization, Content-Type',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    });
    res.end();
    return;
  }

  // Guard: must have storage configured
  if (process.env.VERCEL && !process.env.GITHUB_DATA_TOKEN) {
    return json(res, 503, { success: false, message: 'GITHUB_DATA_TOKEN not configured' });
  }

  // Ensure persist() completes before response flushes
  let endPromise = null;
  const origEnd = res.end.bind(res);
  res.end = function (...args) {
    if (!endPromise) {
      endPromise = persist()
        .catch(err => console.error('[contractai] persist failed:', err))
        .then(() => origEnd(...args));
    }
    return res;
  };

  try {
    await hydrate();
    const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
    await route(req, res, urlPath);
  } catch (e) {
    console.error('[contractai] handler error:', e);
    if (!res.headersSent) {
      json(res, 500, { success: false, message: 'Internal server error' });
    }
  }

  if (endPromise) await endPromise;
  else await persist().catch(() => {});
}

async function route(req, res, path) {
  const method = req.method;

  // Strip /api/v1 prefix if present
  const p = path.replace(/^\/api\/v1/, '') || '/';

  // ─── Auth Status ───────────────────────────────────────────────────────────
  if (p === '/auth/status' && method === 'GET') {
    const user = authUser(req);
    return json(res, 200, {
      bootstrap_required: !hasUsers(),
      authenticated: !!user,
      user: user ? publicUser(user) : undefined,
    });
  }

  // ─── Register ──────────────────────────────────────────────────────────────
  if (p === '/auth/register' && method === 'POST') {
    const body = await readBody(req);
    const { email, password, display_name, org_name } = body;

    if (!email || !password || !display_name) {
      return json(res, 422, { success: false, message: 'email, password, display_name are required' });
    }
    if (password.length < 8) {
      return json(res, 422, { success: false, message: 'Password must be at least 8 characters' });
    }
    if (findUserByEmail(email)) {
      return json(res, 409, { success: false, message: 'Email already registered' });
    }

    // First user becomes owner, subsequent users become member
    const role = hasUsers() ? 'member' : 'owner';
    const user = createUser({ email, password, display_name, org_name, role });
    const access_token = createSession(user.id);
    const refresh_token = createRefreshToken(user.id);

    return json(res, 201, {
      access_token,
      refresh_token,
      user: publicUser(user),
    });
  }

  // ─── Login ─────────────────────────────────────────────────────────────────
  if (p === '/auth/login' && method === 'POST') {
    const body = await readBody(req);
    const { email, password } = body;

    if (!email || !password) {
      return json(res, 422, { success: false, message: 'email and password are required' });
    }

    const user = findUserByEmail(email);
    if (!user || !verifyPassword(password, user.salt, user.hash)) {
      return json(res, 401, { success: false, message: 'Invalid email or password' });
    }

    const access_token = createSession(user.id);
    const refresh_token = createRefreshToken(user.id);

    return json(res, 200, {
      access_token,
      refresh_token,
      user: publicUser(user),
    });
  }

  // ─── Refresh Token ─────────────────────────────────────────────────────────
  if (p === '/auth/refresh' && method === 'POST') {
    const body = await readBody(req);
    const { refresh_token } = body;

    if (!refresh_token) {
      return json(res, 422, { success: false, message: 'refresh_token is required' });
    }

    const session = getSession(refresh_token);
    if (!session || session.type !== 'refresh') {
      return json(res, 401, { success: false, message: 'Invalid refresh token' });
    }

    const user = findUserById(session.userId);
    if (!user) {
      return json(res, 401, { success: false, message: 'User not found' });
    }

    // Rotate tokens
    destroySession(refresh_token);
    const newAccess = createSession(user.id);
    const newRefresh = createRefreshToken(user.id);

    return json(res, 200, {
      access_token: newAccess,
      refresh_token: newRefresh,
      user: publicUser(user),
    });
  }

  // ─── Me ────────────────────────────────────────────────────────────────────
  if (p === '/auth/me' && method === 'GET') {
    const user = authUser(req);
    if (!user) return json(res, 401, { success: false, message: 'Not authenticated' });
    return json(res, 200, publicUser(user));
  }

  // ─── Logout ────────────────────────────────────────────────────────────────
  if (p === '/auth/logout' && method === 'POST') {
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : null;
    if (token) destroySession(token);
    return json(res, 200, { success: true });
  }

  // ─── Change Password ───────────────────────────────────────────────────────
  if (p === '/auth/change-password' && method === 'POST') {
    const user = authUser(req);
    if (!user) return json(res, 401, { success: false, message: 'Not authenticated' });

    const body = await readBody(req);
    const { current_password, new_password } = body;

    if (!verifyPassword(current_password, user.salt, user.hash)) {
      return json(res, 403, { success: false, message: 'Current password is incorrect' });
    }
    if (!new_password || new_password.length < 8) {
      return json(res, 422, { success: false, message: 'New password must be at least 8 characters' });
    }

    const { salt, hash } = hashPassword(new_password);
    user.salt = salt;
    user.hash = hash;
    markUsersDirty();
    return json(res, 200, { success: true });
  }

  // ─── Health ────────────────────────────────────────────────────────────────
  if (p === '/health' || p === '/live') {
    return json(res, 200, { status: 'ok', service: 'ContractGuard', mode: 'serverless' });
  }

  // ─── Fallback ──────────────────────────────────────────────────────────────
  return json(res, 404, { success: false, message: 'Not found: ' + p });
}
