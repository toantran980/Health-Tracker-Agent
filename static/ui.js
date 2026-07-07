import { appMetrics } from './state.js';
import { outputEl, toastContainerEl, statusBannerEl, chatMessagesEl } from './dom.js';

export function writeOutput(title, data) {
  if (outputEl) {
    outputEl.textContent = `${title}\n\n${JSON.stringify(data, null, 2)}`;
    return;
  }
  console.info(title, data);
}

export function showToast(message, type = 'info') {
  if (!toastContainerEl) {
    console.info(`[${type}] ${message}`);
    return;
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastContainerEl.appendChild(toast);
  window.setTimeout(() => { toast.remove(); }, 3200);
}

export function showStatusBanner(message, type = 'error') {
  if (!statusBannerEl) return;
  statusBannerEl.textContent = message;
  statusBannerEl.classList.remove('hidden', 'error', 'info', 'success');
  statusBannerEl.classList.add(type);
}

export function clearStatusBanner() {
  if (!statusBannerEl) return;
  statusBannerEl.textContent = '';
  statusBannerEl.classList.add('hidden');
  statusBannerEl.classList.remove('error', 'info', 'success');
}

export function setElementBusy(el, busy, fallbackLabel = 'Working...') {
  if (!el) return;
  if (busy) {
    if (!el.dataset.originalLabel) {
      el.dataset.originalLabel = (el.textContent || '').trim();
    }
    el.classList.add('is-loading');
    el.disabled = true;
    const original = el.dataset.originalLabel || '';
    el.textContent = original ? `${original}...` : fallbackLabel;
    return;
  }
  el.classList.remove('is-loading');
  el.disabled = false;
  if (el.dataset.originalLabel) {
    el.textContent = el.dataset.originalLabel;
    delete el.dataset.originalLabel;
  }
}

export function setFormBusy(formEl, busy) {
  if (!formEl) return;
  formEl.dataset.busy = busy ? 'true' : 'false';
  const controls = formEl.querySelectorAll('button, input, select, textarea');
  controls.forEach((node) => {
    const tag = node.tagName.toLowerCase();
    if (tag === 'button') {
      if (!busy && node.classList.contains('is-loading')) {
        setElementBusy(node, false);
      } else if (busy && node.type === 'submit') {
        setElementBusy(node, true);
      } else {
        node.disabled = busy;
      }
    } else {
      node.disabled = busy;
    }
  });
}

export function setKpi(prefix, value, status, tone = 'neutral') {
  const valueEl = document.getElementById(`kpi${prefix}`);
  const statusEl = document.getElementById(`kpi${prefix}Status`);
  const cardEl = valueEl ? valueEl.closest('.kpi-card') : null;
  if (valueEl) valueEl.textContent = value;
  if (statusEl) statusEl.textContent = status;
  if (cardEl) cardEl.dataset.status = tone;
}

export function refreshKpis() {
  const caloriesTone = appMetrics.caloriesToday >= 2000 ? 'good' : appMetrics.caloriesToday >= 1200 ? 'warn' : 'neutral';
  const caloriesStatus = appMetrics.caloriesToday === 0 ? 'No meals logged' : appMetrics.caloriesToday >= 2000 ? 'Daily target likely met' : 'Keep fueling';
  setKpi('Calories', `${Math.round(appMetrics.caloriesToday)} kcal`, caloriesStatus, caloriesTone);

  if (appMetrics.focusScore === null) {
    setKpi('Focus', '-', 'Run prediction', 'neutral');
  } else {
    const focusTone = appMetrics.focusScore >= 7 ? 'good' : appMetrics.focusScore >= 5 ? 'warn' : 'bad';
    const focusStatus = appMetrics.focusScore >= 7 ? 'Strong mental state' : appMetrics.focusScore >= 5 ? 'Moderate focus' : 'Low focus window';
    setKpi('Focus', `${appMetrics.focusScore.toFixed(1)}/10`, focusStatus, focusTone);
  }

  const tasksTone = appMetrics.tasksPlanned >= 4 ? 'good' : appMetrics.tasksPlanned > 0 ? 'warn' : 'neutral';
  const tasksStatus = appMetrics.tasksPlanned === 0 ? 'Add tasks' : appMetrics.tasksPlanned >= 4 ? 'Solid plan' : 'Could add more structure';
  setKpi('Tasks', String(appMetrics.tasksPlanned), tasksStatus, tasksTone);

  if (appMetrics.sleepHours === null) {
    setKpi('Sleep', '-', 'Not set', 'neutral');
  } else {
    const sleepTone = appMetrics.sleepHours >= 7 ? 'good' : appMetrics.sleepHours >= 6 ? 'warn' : 'bad';
    const sleepStatus = appMetrics.sleepHours >= 7 ? 'Recovery looks good' : appMetrics.sleepHours >= 6 ? 'Borderline sleep' : 'Prioritize rest';
    setKpi('Sleep', `${appMetrics.sleepHours.toFixed(1)} h`, sleepStatus, sleepTone);
  }
}

export function setChatEmptyState() {
  if (!chatMessagesEl) return;
  chatMessagesEl.innerHTML = '<p class="chat-empty">Start a conversation to get personalized suggestions.</p>';
}

export function appendChatMessage(role, message) {
  if (!chatMessagesEl) return;
  const emptyEl = chatMessagesEl.querySelector('.chat-empty');
  if (emptyEl) emptyEl.remove();
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = message;
  chatMessagesEl.appendChild(bubble);
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

export function switchTab(targetSectionId) {
  document.querySelectorAll('.tab-section').forEach(sec => {
    sec.classList.toggle('tab-hidden', sec.id !== targetSectionId);
  });
  document.querySelectorAll('.hero-link[data-target]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.target === targetSectionId);
  });
}

export function initTabs() {
  document.querySelectorAll('.hero-link[data-target]').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.target));
  });
}
