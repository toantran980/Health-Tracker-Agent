import { apiBaseEl, activeUserEl } from './dom.js';
import { writeOutput } from './ui.js';

let csrfToken = null;
let sessionUserId = '';

export function getApiBase() {
  const savedBase = localStorage.getItem('apiBase');
  if (apiBaseEl) return apiBaseEl.value.trim().replace(/\/$/, '');
  return (savedBase || window.location.origin).trim().replace(/\/$/, '');
}

export function getActiveUserId() {
  const userId = activeUserEl ? activeUserEl.value.trim() : sessionUserId;
  if (!userId) throw new Error('Active User ID is required for this action.');
  return userId;
}

export function setSessionUserId(userId) {
  sessionUserId = (userId || '').trim();
  if (activeUserEl) activeUserEl.value = sessionUserId;
}

/**
 * Normalise an arbitrary fetch failure into a consistent Error carrying the
 * standardized envelope fields: message, code, status, details.
 */
function toApiError(payload, res) {
  const err = new Error(payload && payload.error ? payload.error : `HTTP ${res.status}`);
  err.code = payload && payload.code ? payload.code : 'HTTP_ERROR';
  err.status = res.status;
  if (payload && payload.details !== undefined) err.details = payload.details;
  return err;
}

/**
 * Lazily obtain the session CSRF token. It is exposed by GET /api/auth/me
 * (and by the login response) and must be echoed on state-changing requests
 * when a session is active.
 */
export async function getCsrfToken() {
  if (csrfToken) return csrfToken;
  try {
    const payload = await apiRequest('/api/auth/me', { skipCsrf: true });
    if (payload && payload.csrf_token) csrfToken = payload.csrf_token;
  } catch {
    // Server unreachable — the following request will surface the real error.
  }
  return csrfToken;
}

export function setCsrfToken(token) {
  if (token) csrfToken = token;
}

const CSRF_EXEMPT_PATHS = ['/api/auth/login', '/api/user/create'];

export async function apiRequest(path, options = {}) {
  const url = `${getApiBase()}${path}`;
  const config = {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
  };
  if (options.body !== undefined) config.body = JSON.stringify(options.body);

  const writeMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method);
  if (writeMethod && !options.skipCsrf && !CSRF_EXEMPT_PATHS.includes(path)) {
    const token = await getCsrfToken();
    if (token) config.headers['X-CSRF-Token'] = token;
  }

  let res;
  try {
    res = await fetch(url, config);
  } catch (networkErr) {
    // Network failure (server unreachable, DNS, CORS) — keep the envelope shape.
    const err = new Error(networkErr.message || `Could not reach ${url}`);
    err.code = 'NETWORK_ERROR';
    err.status = null;
    throw err;
  }

  const raw = await res.text();
  let payload;
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch {
    payload = { raw };
  }

  if (!res.ok) {
    throw toApiError(payload, res);
  }
  return payload;
}

export async function requestForActiveUser(title, pathFactory, options = {}) {
  const userId = getActiveUserId();
  const payload = await apiRequest(pathFactory(userId), options);
  writeOutput(title, payload);
  return payload;
}

export async function getAuthStatus() {
  try {
    const payload = await apiRequest('/api/auth/me', { skipCsrf: true });
    if (payload.csrf_token) setCsrfToken(payload.csrf_token);
    return { ok: true, payload };
  } catch (err) {
    return { ok: false, err };
  }
}

export async function login(userId, password) {
  if (!userId) throw new Error('Active User ID is required to log in.');
  if (!password) throw new Error('Password is required to log in.');
  const payload = await apiRequest('/api/auth/login', { method: 'POST', body: { user_id: userId, password }, skipCsrf: true });
  if (payload.csrf_token) setCsrfToken(payload.csrf_token);
  setSessionUserId(payload.user_id);
  return payload;
}

export async function logout() {
  const payload = await apiRequest('/api/auth/logout', { method: 'POST' });
  setCsrfToken(null);
  setSessionUserId('');
  return payload;
}