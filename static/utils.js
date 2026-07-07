import { setFormBusy, setElementBusy, clearStatusBanner, showToast, showStatusBanner, writeOutput } from './ui.js';

export function safeHandler(handler, contextEl = null) {
  return async (event) => {
    if (event) event.preventDefault();
    const formEl = event && event.target instanceof HTMLFormElement ? event.target : null;
    const submitter = event && event.submitter ? event.submitter : null;
    const busyEl = submitter || contextEl;
    try {
      if (formEl) setFormBusy(formEl, true);
      else setElementBusy(busyEl, true);
      clearStatusBanner();
      await handler(event);
    } catch (err) {
      const errorPayload = {
        message: err.message || 'Unknown error',
        code: err.code || 'UNKNOWN_ERROR',
        status: err.status || null
      };
      showToast(`${errorPayload.message} (${errorPayload.code})`, 'error');
      showStatusBanner(`${errorPayload.message} [${errorPayload.code}]`, 'error');
      writeOutput('Error', errorPayload);
    } finally {
      if (formEl) setFormBusy(formEl, false);
      else setElementBusy(busyEl, false);
    }
  };
}

export function bindClick(id, handler) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('click', safeHandler(handler, el));
}

export function bindSubmit(id, handler) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('submit', safeHandler(async (event) => {
    await handler(event.target);
  }, el));
}
