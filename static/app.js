// Fetch and display model evaluation metrics
async function fetchModelMetrics() {
  const maeEl = document.getElementById('metricProductivityMAE');
  const nEl = document.getElementById('metricProductivityN');
  if (!maeEl || !nEl) return;
  try {
    const res = await fetch('/api/metrics/productivity_predictor');
    if (!res.ok) throw new Error('Failed to fetch metrics');
    const data = await res.json();
    if (data.mae !== undefined && data.n !== undefined) {
      maeEl.textContent = data.mae !== null ? data.mae.toFixed(2) : '-';
      nEl.textContent = `Test cases: ${data.n}`;
    } else {
      maeEl.textContent = '-';
      nEl.textContent = 'No data';
    }
  } catch (err) {
    maeEl.textContent = '-';
    nEl.textContent = 'Error loading metrics';
  }
}

window.addEventListener('DOMContentLoaded', fetchModelMetrics);
const outputEl = document.getElementById('output');
const apiBaseEl = document.getElementById('apiBase');
const activeUserEl = document.getElementById('activeUserId');
const taskListEl = document.getElementById('taskList');
const taskSummaryEl = document.getElementById('taskSummary');
const toastContainerEl = document.getElementById('toastContainer');
const chatMessagesEl = document.getElementById('chatMessages');
const statusBannerEl = document.getElementById('statusBanner');

const appMetrics = {
  caloriesToday: 0,
  focusScore: null,
  tasksPlanned: 0,
  sleepHours: null
};

const savedBase = localStorage.getItem('apiBase');
const savedUser = localStorage.getItem('activeUserId');
if (apiBaseEl) {
  apiBaseEl.value = savedBase || window.location.origin;
  // Save on both input and change for immediate persistence
  apiBaseEl.addEventListener('input', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
  apiBaseEl.addEventListener('change', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
}
if (activeUserEl) {
  activeUserEl.value = savedUser || '';
  // Save on both input and change for immediate persistence
  activeUserEl.addEventListener('input', () => localStorage.setItem('activeUserId', activeUserEl.value.trim()));
  activeUserEl.addEventListener('change', () => localStorage.setItem('activeUserId', activeUserEl.value.trim()));
}

function writeOutput(title, data) {
  if (outputEl) {
    outputEl.textContent = `${title}\n\n${JSON.stringify(data, null, 2)}`;
    return;
  }
  console.info(title, data);
}

function showToast(message, type = 'info') {
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

function showStatusBanner(message, type = 'error') {
  if (!statusBannerEl) return;
  statusBannerEl.textContent = message;
  statusBannerEl.classList.remove('hidden', 'error', 'info', 'success');
  statusBannerEl.classList.add(type);
}

function clearStatusBanner() {
  if (!statusBannerEl) return;
  statusBannerEl.textContent = '';
  statusBannerEl.classList.add('hidden');
  statusBannerEl.classList.remove('error', 'info', 'success');
}

function setElementBusy(el, busy, fallbackLabel = 'Working...') {
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

function setFormBusy(formEl, busy) {
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

function setKpi(prefix, value, status, tone = 'neutral') {
  const valueEl = document.getElementById(`kpi${prefix}`);
  const statusEl = document.getElementById(`kpi${prefix}Status`);
  const cardEl = valueEl ? valueEl.closest('.kpi-card') : null;
  if (valueEl) valueEl.textContent = value;
  if (statusEl) statusEl.textContent = status;
  if (cardEl) cardEl.dataset.status = tone;
}

function refreshKpis() {
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

function setChatEmptyState() {
  if (!chatMessagesEl) return;
  chatMessagesEl.innerHTML = '<p class="chat-empty">Start a conversation to get personalized suggestions.</p>';
}

function appendChatMessage(role, message) {
  if (!chatMessagesEl) return;
  const emptyEl = chatMessagesEl.querySelector('.chat-empty');
  if (emptyEl) emptyEl.remove();
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = message;
  chatMessagesEl.appendChild(bubble);
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

function switchTab(targetSectionId) {
  document.querySelectorAll('.tab-section').forEach(sec => {
    sec.classList.toggle('tab-hidden', sec.id !== targetSectionId);
  });
  document.querySelectorAll('.hero-link[data-target]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.target === targetSectionId);
  });
}

function initTabs() {
  document.querySelectorAll('.hero-link[data-target]').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.target));
  });
}

function initQuickActions() {
  const routeTo = (sectionId, focusSelector) => {
    switchTab(sectionId);
    if (focusSelector) {
      const sec = document.getElementById(sectionId);
      const focusEl = sec && sec.querySelector(focusSelector);
      if (focusEl) window.setTimeout(() => focusEl.focus(), 80);
    }
  };
  bindClick('quickLogMeal', async () => routeTo('section-nutrition', 'input[name="food_name"]'));
  bindClick('quickPredictFocus', async () => routeTo('section-schedule', 'input[name="hour_of_day"]'));
  bindClick('quickOptimizeSchedule', async () => routeTo('section-schedule', null));
  bindClick('quickAskChatbot', async () => routeTo('section-chat', 'input[name="message"]'));
}

function getApiBase() {
  if (apiBaseEl) return apiBaseEl.value.trim().replace(/\/$/, '');
  return (savedBase || window.location.origin).trim().replace(/\/$/, '');
}

function getActiveUserId() {
  const userId = activeUserEl ? activeUserEl.value.trim() : (localStorage.getItem('activeUserId') || '').trim();
  if (!userId) throw new Error('Active User ID is required for this action.');
  return userId;
}

async function apiRequest(path, options = {}) {
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

function safeHandler(handler, contextEl = null) {
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

function bindClick(id, handler) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('click', safeHandler(handler, el));
}

function bindSubmit(id, handler) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('submit', safeHandler(async (event) => {
    await handler(event.target);
  }, el));
}

async function requestForActiveUser(title, pathFactory, options = {}) {
  const userId = getActiveUserId();
  const payload = await apiRequest(pathFactory(userId), options);
  writeOutput(title, payload);
  return payload;
}

const trendState = { labels: [], calories: [], protein: [], carbs: [], fat: [], focus: [] };
let caloriesChart, macrosChart, focusChart;

function timestampLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function capTrendPoints(max = 10) {
  while (trendState.labels.length > max) {
    trendState.labels.shift(); trendState.calories.shift(); trendState.protein.shift();
    trendState.carbs.shift(); trendState.fat.shift(); trendState.focus.shift();
  }
}

function updateCharts() {
  const scrollX = window.scrollX;
  const scrollY = window.scrollY;
  caloriesChart.data.labels = trendState.labels;
  caloriesChart.data.datasets[0].data = trendState.calories;
  caloriesChart.update('none');
  macrosChart.data.labels = trendState.labels;
  macrosChart.data.datasets[0].data = trendState.protein;
  macrosChart.data.datasets[1].data = trendState.carbs;
  macrosChart.data.datasets[2].data = trendState.fat;
  macrosChart.update('none');
  focusChart.data.labels = trendState.labels;
  focusChart.data.datasets[0].data = trendState.focus;
  focusChart.update('none');
  requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));
}

function addTrendPoint(values) {
  trendState.labels.push(timestampLabel());
  trendState.calories.push(values.calories ?? null);
  trendState.protein.push(values.protein ?? null);
  trendState.carbs.push(values.carbs ?? null);
  trendState.fat.push(values.fat ?? null);
  trendState.focus.push(values.focus ?? null);
  capTrendPoints();
  updateCharts();
}

function initCharts() {
  const commonOptions = {
    responsive: true, maintainAspectRatio: false, animation: false,
    scales: { y: { beginAtZero: true } }
  };
  caloriesChart = new Chart(document.getElementById('caloriesChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Calories', data: [], borderColor: '#0f6f5f', backgroundColor: 'rgba(15, 111, 95, 0.2)', tension: 0.25 }] },
    options: commonOptions
  });
  macrosChart = new Chart(document.getElementById('macrosChart'), {
    type: 'line',
    data: { labels: [], datasets: [
      { label: 'Protein', data: [], borderColor: '#2b7a4b', tension: 0.25 },
      { label: 'Carbs',   data: [], borderColor: '#c07f2b', tension: 0.25 },
      { label: 'Fat',     data: [], borderColor: '#8c4fa3', tension: 0.25 }
    ]},
    options: commonOptions
  });
  focusChart = new Chart(document.getElementById('focusChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Focus Score', data: [], borderColor: '#1f4f8a', backgroundColor: 'rgba(31, 79, 138, 0.2)', tension: 0.25 }] },
    options: { ...commonOptions, scales: { y: { beginAtZero: true, suggestedMax: 10 } } }
  });
}

function createTaskRow(task = {}) {
  const row = document.createElement('div');
  row.className = 'task-row';
  row.innerHTML = `
    <label>Title<input type="text" class="task-title" value="${task.title || ''}" placeholder="Task title"></label>
    <label>Duration<input type="number" class="task-duration" min="1" value="${task.duration_minutes || 60}"></label>
    <label>Difficulty<input type="number" class="task-difficulty" min="1" max="10" value="${task.difficulty || 5}"></label>
    <label>Deadline (days)<input type="number" class="task-deadline" min="0" value="${task.deadline_days || 1}"></label>
    <button type="button" class="btn btn-remove-task">Remove</button>
  `;
  row.querySelector('.btn-remove-task').addEventListener('click', () => { row.remove(); updateTaskSummary(); });
  row.querySelectorAll('input').forEach((input) => { input.addEventListener('input', updateTaskSummary); });
  return row;
}

function updateTaskSummary() {
  const tasks = collectTasks(false);
  const totalDuration = tasks.reduce((sum, task) => sum + (task.duration_minutes || 0), 0);
  taskSummaryEl.textContent = `Total tasks: ${tasks.length} | Total duration: ${totalDuration} min`;
  appMetrics.tasksPlanned = tasks.length;
  refreshKpis();
}

function collectTasks(strict = true) {
  const rows = Array.from(taskListEl.querySelectorAll('.task-row'));
  const tasks = rows.map((row) => ({
    title:            row.querySelector('.task-title').value.trim(),
    duration_minutes: Number(row.querySelector('.task-duration').value),
    difficulty:       Number(row.querySelector('.task-difficulty').value),
    deadline_days:    Number(row.querySelector('.task-deadline').value)
  }));

  if (!strict) return tasks.filter((t) => t.title || t.duration_minutes || t.difficulty || t.deadline_days);
  if (tasks.length === 0) throw new Error('Add at least one task before optimizing.');
  tasks.forEach((task, index) => {
    if (!task.title) throw new Error(`Task ${index + 1}: title is required.`);
    if (!Number.isFinite(task.duration_minutes) || task.duration_minutes <= 0) throw new Error(`Task ${index + 1}: duration must be greater than 0.`);
    if (!Number.isFinite(task.difficulty) || task.difficulty < 1 || task.difficulty > 10) throw new Error(`Task ${index + 1}: difficulty must be between 1 and 10.`);
    if (!Number.isFinite(task.deadline_days) || task.deadline_days < 0) throw new Error(`Task ${index + 1}: deadline days must be 0 or more.`);
  });
  return tasks;
}

function initTaskBuilder() {
  document.getElementById('btnAddTask').addEventListener('click', () => {
    taskListEl.appendChild(createTaskRow());
    updateTaskSummary();
  });
  updateTaskSummary();
}

// ── Create User ──────────────────────────────────────────────────────────────
bindSubmit('createUserForm', async (form) => {
  const name      = form.elements['name'].value.trim();
  const age       = Number(form.elements['age'].value);
  const weight_kg = Number(form.elements['weight_kg'].value);
  const height_cm = Number(form.elements['height_cm'].value);

  if (!name)                        throw new Error('Name is required.');
  if (!age || age < 1)              throw new Error('Valid age is required.');
  if (!weight_kg || weight_kg < 1)  throw new Error('Valid weight is required.');
  if (!height_cm || height_cm < 1)  throw new Error('Valid height is required.');

  const body = {
    name,
    age,
    biological_sex:   form.elements['biological_sex'].value || 'male',
    weight_kg,
    height_cm,
    goals:            [form.elements['goal'].value || 'general_wellness'],
    target_calories:  Number(form.elements['target_calories'].value)  || 2000,
    target_protein_g: Number(form.elements['target_protein_g'].value) || 150,
    target_carbs_g:   Number(form.elements['target_carbs_g'].value)   || 200,
    target_fat_g:     Number(form.elements['target_fat_g'].value)     || 65,
  };

  const payload = await apiRequest('/api/user/create', { method: 'POST', body });
  if (payload.user && payload.user.user_id) {
    if (activeUserEl) activeUserEl.value = payload.user.user_id;
    localStorage.setItem('activeUserId', payload.user.user_id);
  }
  showToast('User profile created.', 'success');
  writeOutput('User Created', payload);
});

bindClick('btnGetUser', async () => {
  await requestForActiveUser('User Profile', (userId) => `/api/user/${userId}`);
});

// ── Log Meal ─────────────────────────────────────────────────────────────────
bindSubmit('mealForm', async (form) => {
  const userId = getActiveUserId();
  const body = {
    meal_type: form.elements['meal_type'].value || 'lunch',
    food_items: [{
      name:      form.elements['food_name'].value || 'Unknown food',
      calories:  Number(form.elements['calories'].value)  || 0,
      protein_g: Number(form.elements['protein_g'].value) || 0,
      carbs_g:   Number(form.elements['carbs_g'].value)   || 0,
      fat_g:     Number(form.elements['fat_g'].value)     || 0,
    }]
  };
  const payload = await apiRequest(`/api/nutrition/log-meal/${userId}`, { method: 'POST', body });
  if (payload.nutrition) {
    appMetrics.caloriesToday += Number(payload.nutrition.calories || 0);
    refreshKpis();
    addTrendPoint({
      calories: payload.nutrition.calories,
      protein:  payload.nutrition.protein_g,
      carbs:    payload.nutrition.carbs_g,
      fat:      payload.nutrition.fat_g
    });
  }
  showToast('Meal logged.', 'success');
  writeOutput('Meal Logged', payload);
});

bindClick('btnAnalyze', async () => {
  await requestForActiveUser('Nutrition Analysis', (userId) => `/api/nutrition/analysis/${userId}`);
  showToast('Nutrition analysis ready.', 'info');
});

bindClick('btnMacroRecs', async () => {
  await requestForActiveUser('Macro Recommendations', (userId) => `/api/nutrition/recommendations/${userId}`);
  showToast('Macro recommendations loaded.', 'info');
});

// ── Meal Recommendations ──────────────────────────────────────────────────────
bindSubmit('mealRecForm', async (form) => {
  const userId = getActiveUserId();
  const params = new URLSearchParams({
    target_calories: String(Number(form.elements['target_calories'].value) || 650),
    target_protein:  String(Number(form.elements['target_protein'].value)  || 35),
    mode:            form.elements['mode'].value || 'constraint',
    n:               String(Number(form.elements['n'].value) || 5)
  });
  const payload = await apiRequest(`/api/nutrition/meal-recommendations/${userId}?${params.toString()}`);
  showToast('Meal recommendations loaded.', 'info');
  writeOutput('Meal Recommendations', payload);
});

// ── Schedule ──────────────────────────────────────────────────────────────────
bindSubmit('scheduleForm', async () => {
  const tasks = collectTasks(true);
  await requestForActiveUser('Optimized Schedule', (userId) => `/api/schedule/optimize/${userId}`, {
    method: 'POST', body: { tasks }
  });
  showToast('Schedule optimized.', 'success');
});

bindClick('btnSlots', async () => {
  await requestForActiveUser('Available Slots', (userId) => `/api/schedule/available-slots/${userId}?duration_minutes=60`);
  showToast('Available slots loaded.', 'info');
});

// ── Productivity ──────────────────────────────────────────────────────────────
bindSubmit('productivityForm', async (form) => {
  const userId = getActiveUserId();
  const body = {
    hour_of_day:               Number(form.elements['hour_of_day'].value)               || 0,
    day_of_week:               Number(form.elements['day_of_week'].value)               || 0,
    sleep_quality:             Number(form.elements['sleep_quality'].value)             || 7,
    sleep_hours:               Number(form.elements['sleep_hours'].value)               || 8,
    nutrition_score:           Number(form.elements['nutrition_score'].value)           || 75,
    energy_level:              Number(form.elements['energy_level'].value)              || 7,
    previous_session_duration: Number(form.elements['previous_session_duration'].value) || 60,
    task_difficulty:           Number(form.elements['task_difficulty'].value)           || 5,
  };
  const payload = await apiRequest(`/api/productivity/predict/${userId}`, { method: 'POST', body });
  if (payload.predicted_focus_score !== undefined) {
    appMetrics.focusScore = Number(payload.predicted_focus_score);
    appMetrics.sleepHours = body.sleep_hours;
    refreshKpis();
    addTrendPoint({ focus: payload.predicted_focus_score });
  }
  showToast('Focus prediction updated.', 'success');
  writeOutput('Productivity Prediction', payload);
});

bindClick('btnOptimalTime', async () => {
  await requestForActiveUser('Optimal Study Time', (userId) => `/api/productivity/optimal-time/${userId}`);
  showToast('Optimal time generated.', 'info');
});

// ── Chatbot ───────────────────────────────────────────────────────────────────
bindSubmit('chatForm', async (form) => {
  const userId  = getActiveUserId();
  const message = form.elements['message'].value.trim();
  if (!message) throw new Error('Message is required.');
  appendChatMessage('user', message);
  const payload = await apiRequest(`/api/chat/${userId}`, { method: 'POST', body: { message } });
  appendChatMessage('assistant', payload.reply || 'No response from chatbot.');
  showToast('Chatbot replied.', 'success');
  form.reset();
  writeOutput('Chatbot Reply', payload);
});

bindClick('btnResetChat', async () => {
  await requestForActiveUser('Chatbot Reset', (userId) => `/api/chat/${userId}/reset`, { method: 'POST' });
  setChatEmptyState();
  showToast('Chat reset complete.', 'info');
});

// ── Insights ──────────────────────────────────────────────────────────────────
bindClick('btnInsights', async () => {
  await requestForActiveUser('Health Insights', (userId) => `/api/insights/${userId}`);
  showToast('Insights generated.', 'info');
});

bindClick('btnKnowledgeRecs', async () => {
  // Try to get values from input fields; fallback to defaults if not present
  const getVal = (id, fallback) => {
    const el = document.getElementById(id);
    if (!el) return fallback;
    if (el.type === 'number') return Number(el.value) || fallback;
    if (el.type === 'checkbox') return el.checked;
    return el.value || fallback;
  };

  const body = {
    daily_calories: Number(getVal('kbDailyCalories', 2000)),
    daily_protein: Number(getVal('kbDailyProtein', 130)),
    energy_level: Number(getVal('kbEnergyLevel', 7)),
    sleep_hours: Number(getVal('kbSleepHours', 7.5)),
    upcoming_difficulty: Number(getVal('kbUpcomingDifficulty', 6)),
    recent_session_duration: Number(getVal('kbRecentSessionDuration', 60)),
    macro_balance: getVal('kbMacroBalance', 'balanced'),
    macro_balance_details: {
      protein: getVal('kbMacroProtein', 'ok'),
      carbs: getVal('kbMacroCarbs', 'ok'),
      fat: getVal('kbMacroFat', 'ok')
    },
    correlation_nutrition_study: Number(getVal('kbCorrelationNutritionStudy', 0.4)),
    adherence_rate: Number(getVal('kbAdherenceRate', 0.7))
  };
  await requestForActiveUser('Knowledge Base Recommendations', (userId) => `/api/recommendations/${userId}`, {
    method: 'POST', body
  });
  showToast('Knowledge recommendations ready.', 'info');
});

// ── Init ──────────────────────────────────────────────────────────────────────
initTabs();
initTaskBuilder();
initCharts();
initQuickActions();
setChatEmptyState();
refreshKpis();