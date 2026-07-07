import { apiBaseEl, activeUserEl } from './dom.js';
import { writeOutput } from './ui.js';

export function getApiBase() {
  const savedBase = localStorage.getItem('apiBase');
  if (apiBaseEl) return apiBaseEl.value.trim().replace(/\/$/, '');
  return (savedBase || window.location.origin).trim().replace(/\/$/, '');
}

export function getActiveUserId() {
  const userId = activeUserEl ? activeUserEl.value.trim() : (localStorage.getItem('activeUserId') || '').trim();
  if (!userId) throw new Error('Active User ID is required for this action.');
  return userId;
}

export async function apiRequest(path, options = {}) {
  const url = `${getApiBase()}${path}`;
  const config = {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
  };
  if (options.body !== undefined) config.body = JSON.stringify(options.body);

  const res = await fetch(url, config);
  const raw = await res.text();
  let payload;
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch {
    payload = { raw };
  }

  if (!res.ok) {
    const msg = payload && payload.error ? payload.error : `HTTP ${res.status}`;
    const err = new Error(msg);
    err.code = payload && payload.code ? payload.code : 'HTTP_ERROR';
    err.status = res.status;
    throw err;
  }
  return payload;
}

export async function requestForActiveUser(title, pathFactory, options = {}) {
  const userId = getActiveUserId();
  const payload = await apiRequest(pathFactory(userId), options);
  writeOutput(title, payload);
  return payload;
}
