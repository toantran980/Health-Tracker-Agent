import { apiBaseEl, activeUserEl } from './dom.js';
import { appMetrics } from './state.js';
import { apiRequest, requestForActiveUser, getActiveUserId, getAuthStatus, setSessionUserId, login, logout } from './api.js';
import { initTabs, setChatEmptyState, refreshKpis, writeOutput, showToast, switchTab, appendChatMessage, removeLastChatMessage, showStatusBanner } from './ui.js';
import { initCharts, addTrendPoint, setTrendData } from './charts.js';
import { initTaskBuilder, collectTasks } from './tasks.js';
import { bindClick, bindSubmit } from './utils.js';
import { DEFAULTS } from './config.js';

const savedBase = localStorage.getItem('apiBase');
// Clear any stale active-user id persisted by older versions so it no longer
// auto-restores on page load / server restart.
localStorage.removeItem('activeUserId');

const PROTECTED_CONTROL_IDS = [
  'btnGetUser',
  'mealForm',
  'btnAnalyze',
  'btnMacroRecs',
  'mealRecForm',
  'scheduleForm',
  'btnSlots',
  'productivityForm',
  'btnOptimalTime',
  'chatForm',
  'btnResetChat',
  'btnInsights',
  'btnKnowledgeRecs',
  'btnHealthRisks',
  'btnRecovery',
  'btnGoals',
  'btnDigest',
  'btnSleepPredict',
  'btnActivityRecs',
  'activityLogForm',
  'btnActivityLogs',
  'btnActivityTrends',
  'btnScheduleHistory',
  'btnProductivitySessions',
];

function setAuthGate(authenticated) {
  for (const id of PROTECTED_CONTROL_IDS) {
    const el = document.getElementById(id);
    if (!el) continue;
    // If the ID corresponds to a form, disable the entire form
    if (el instanceof HTMLFormElement) {
      el.querySelectorAll('input, button, select').forEach((t) => { t.disabled = !authenticated; });
    } else {
      // For buttons and other individual elements, only disable that specific element
      el.disabled = !authenticated;
    }
  }
}

if (apiBaseEl) {
  apiBaseEl.value = savedBase || window.location.origin;
  apiBaseEl.addEventListener('input', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
  apiBaseEl.addEventListener('change', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
}

async function fetchModelMetrics() {
  const maeEl  = document.getElementById('metricProductivityMAE');
  const rmseEl = document.getElementById('metricProductivityRMSE');
  const r2El   = document.getElementById('metricProductivityR2');
  const nEl    = document.getElementById('metricProductivityN');
  if (!maeEl || !nEl) return;
  try {
    const res  = await fetch('/api/metrics/productivity_predictor');
    if (!res.ok) throw new Error('Failed to fetch metrics');
    const data = await res.json();
    maeEl.textContent  = data.mae  != null ? data.mae.toFixed(2)  : '-';
    if (rmseEl) rmseEl.textContent = data.rmse != null ? data.rmse.toFixed(2) : '-';
    if (r2El)   r2El.textContent   = data.r2   != null ? data.r2.toFixed(3)   : '-';
    nEl.textContent = `Test cases: ${data.n}`;
  } catch (err) {
    maeEl.textContent = '-';
    nEl.textContent   = 'Error loading metrics';
  }
}
window.addEventListener('DOMContentLoaded', fetchModelMetrics);

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
    name, age,
    biological_sex:   form.elements['biological_sex'].value || DEFAULTS.USER.BIOLOGICAL_SEX,
    weight_kg, height_cm,
    goals:            [form.elements['goal'].value || DEFAULTS.USER.GOALS[0]],
    target_calories:  Number(form.elements['target_calories'].value)  || DEFAULTS.USER.TARGET_CALORIES,
    target_protein_g: Number(form.elements['target_protein_g'].value) || DEFAULTS.USER.TARGET_PROTEIN,
    target_carbs_g:   Number(form.elements['target_carbs_g'].value)   || DEFAULTS.USER.TARGET_CARBS,
    target_fat_g:     Number(form.elements['target_fat_g'].value)     || DEFAULTS.USER.TARGET_FAT,
    water_target_ml:  Number(form.elements['water_target_ml'].value)  || DEFAULTS.USER.WATER_TARGET,
  };

  const password = form.elements['password'] ? form.elements['password'].value : '';
  if (password) body.password = password;

  const payload = await apiRequest('/api/user/create', { method: 'POST', body });
  if (payload.user && payload.user.user_id) {
    if (activeUserEl) activeUserEl.value = payload.user.user_id;
  }
  showToast('User profile created.', 'success');
  writeOutput('User Created', payload);
});

bindSubmit('loginForm', async (form) => {
  const userId = form.elements['user_id'].value.trim() || getActiveUserId();
  const password = form.elements['password'].value;
  const payload = await login(userId, password);
  if (payload.user_id) {
    if (activeUserEl) activeUserEl.value = payload.user_id;
  }
  form.reset();
  showToast(`Logged in as ${payload.user_id}.`, 'success');
  writeOutput('Login', payload);
  updateAuthStatus();
});

bindClick('btnLogout', async () => {
  await logout();
  showToast('Logged out.', 'info');
  writeOutput('Logout', { status: 'logged_out' });
  updateAuthStatus();
});

async function updateAuthStatus() {
  const el = document.getElementById('authStatus');
  if (!el) return;
  const { ok, payload } = await getAuthStatus();
  if (!ok) {
    el.hidden = false;
    el.textContent = 'Session could not be checked (is the server running?).';
    return;
  }
  if (payload && payload.authenticated) {
    setSessionUserId(payload.user_id);
    el.hidden = false;
    el.textContent = `Logged in as: ${payload.user_id}`;
    el.style.color = 'var(--success, #2ecc71)';
    el.title = '';
  } else {
    setSessionUserId('');
    el.hidden = true;
    el.textContent = '';
    el.title = '';
  }
  setAuthGate(!!(payload && payload.authenticated));
  if (payload && payload.authenticated && payload.user_id) {
    loadTrends(payload.user_id);
  }
}

async function loadTrends(userId) {
  try {
    const rangeEl = document.getElementById('trendsTimeRange');
    const days = rangeEl ? parseInt(rangeEl.value, 10) : 7;
    const payload = await apiRequest(`/api/trends/${encodeURIComponent(userId)}?days=${days}`);
    if (payload && payload.nutrition) {
      setTrendData(payload.nutrition, payload.focus);
    }
  } catch (err) {
    if (err && err.code === 'AUTH_REQUIRED') {
      setAuthGate(false);
    }
  }
}

bindClick('btnGetUser', async () => {
  await requestForActiveUser('User Profile', (userId) => `/api/user/${userId}`);
});

bindSubmit('mealForm', async (form) => {
  const userId = getActiveUserId();
  const body = {
    user_id: userId,
    meal_type: form.elements['meal_type'].value || DEFAULTS.MEAL.TYPE,
    food_items: [{
      name:      form.elements['food_name'].value || DEFAULTS.MEAL.NAME,
      calories:  Number(form.elements['calories'].value)  || DEFAULTS.MEAL.CALORIES,
      protein_g: Number(form.elements['protein_g'].value) || DEFAULTS.MEAL.PROTEIN,
      carbs_g:   Number(form.elements['carbs_g'].value)   || DEFAULTS.MEAL.CARBS,
      fat_g:     Number(form.elements['fat_g'].value)     || DEFAULTS.MEAL.FAT,
    }]
  };
  const payload = await apiRequest('/api/meals/log', { method: 'POST', body });
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

bindSubmit('mealRecForm', async (form) => {
  const userId = getActiveUserId();
  const params = new URLSearchParams({
    target_calories: String(Number(form.elements['target_calories'].value) || DEFAULTS.MEAL_REC.TARGET_CALORIES),
    target_protein:  String(Number(form.elements['target_protein'].value)  || DEFAULTS.MEAL_REC.TARGET_PROTEIN),
    mode:            form.elements['mode'].value || DEFAULTS.MEAL_REC.MODE,
    n:               String(Number(form.elements['n'].value) || DEFAULTS.MEAL_REC.COUNT)
  });
  const payload = await apiRequest(`/api/nutrition/meal-recommendations/${userId}?${params.toString()}`);
  showToast('Meal recommendations loaded.', 'info');
  writeOutput('Meal Recommendations', payload);
});

bindSubmit('scheduleForm', async () => {
  const tasks = collectTasks(true);
  await requestForActiveUser('Optimized Schedule', (userId) => `/api/schedule/optimize/${userId}`, {
    method: 'POST', body: { tasks }
  });
  showToast('Schedule optimized.', 'success');
});

bindClick('btnSlots', async () => {
  await requestForActiveUser('Available Slots', (userId) => `/api/schedule/available-slots/${userId}?duration_minutes=${DEFAULTS.SCHEDULE.DURATION_MINUTES}`);
  showToast('Available slots loaded.', 'info');
});

bindSubmit('productivityForm', async (form) => {
  const userId = getActiveUserId();
  const body = {
    hour_of_day:               Number(form.elements['hour_of_day'].value)               || DEFAULTS.PRODUCTIVITY.HOUR_OF_DAY,
    day_of_week:               Number(form.elements['day_of_week'].value)               || DEFAULTS.PRODUCTIVITY.DAY_OF_WEEK,
    sleep_quality:             Number(form.elements['sleep_quality'].value)             || DEFAULTS.PRODUCTIVITY.SLEEP_QUALITY,
    sleep_hours:               Number(form.elements['sleep_hours'].value)               || DEFAULTS.PRODUCTIVITY.SLEEP_HOURS,
    nutrition_score:           Number(form.elements['nutrition_score'].value)           || DEFAULTS.PRODUCTIVITY.NUTRITION_SCORE,
    energy_level:              Number(form.elements['energy_level'].value)              || DEFAULTS.PRODUCTIVITY.ENERGY_LEVEL,
    previous_session_duration: Number(form.elements['previous_session_duration'].value) || DEFAULTS.PRODUCTIVITY.PREV_SESSION_DURATION,
    task_difficulty:           Number(form.elements['task_difficulty'].value)           || DEFAULTS.PRODUCTIVITY.TASK_DIFFICULTY,
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

bindSubmit('chatForm', async (form) => {
  const userId  = getActiveUserId();
  const message = form.elements['message'].value.trim();
  if (!message) throw new Error('Message is required.');
  appendChatMessage('user', message);
  try {
    const payload = await apiRequest(`/api/chat/${userId}`, { method: 'POST', body: { message } });
    appendChatMessage('assistant', payload.reply || 'No response from chatbot.', payload.provider);
    showToast('Chatbot replied.', 'success');
    form.reset();
    writeOutput('Chatbot Reply', payload);
  } catch (err) {
    if (err && err.code === 'AUTH_REQUIRED') {
      removeLastChatMessage('user');
      showToast('Log in to chat — your message was kept.', 'error');
      showStatusBanner('Log in to continue chatting.', 'error');
      throw err;
    }
    throw err;
  }
});

bindClick('btnResetChat', async () => {
  await requestForActiveUser('Chatbot Reset', (userId) => `/api/chat/${userId}/reset`, { method: 'POST' });
  setChatEmptyState();
  showToast('Chat reset complete.', 'info');
});

bindClick('btnInsights', async () => {
  await requestForActiveUser('Health Insights', (userId) => `/api/insights/${userId}`);
  showToast('Insights generated.', 'info');
});

function showInsightResult(title, payload) {
  const result = document.getElementById('insightResult');
  if (!result) return;
  const entries = Object.entries(payload || {})
    .filter(([key, value]) => !['user_id', 'assessed_at'].includes(key) && value !== null && typeof value !== 'object')
    .slice(0, 6);
  result.replaceChildren();
  const heading = document.createElement('strong');
  heading.textContent = title;
  result.appendChild(heading);
  if (!entries.length) {
    result.appendChild(document.createTextNode(' Ready for more logged data.'));
    return;
  }
  entries.forEach(([key, value]) => {
    const line = document.createElement('span');
    line.textContent = `${key.replaceAll('_', ' ')}: ${value}`;
    result.appendChild(line);
  });
}

async function loadInsight(title, path) {
  const payload = await requestForActiveUser(title, path);
  showInsightResult(title, payload);
  showToast(`${title} ready.`, 'info');
}

bindClick('btnHealthRisks', () => loadInsight('Health Risks', (userId) => `/api/health-risks/${userId}`));
bindClick('btnRecovery', () => loadInsight('Recovery Readiness', (userId) => `/api/recovery/${userId}`));
bindClick('btnGoals', () => loadInsight('Goal Progress', (userId) => `/api/goals/${userId}`));
bindClick('btnDigest', () => loadInsight('Weekly Digest', (userId) => `/api/digest/${userId}`));
bindClick('btnSleepPredict', () => loadInsight('Sleep Quality', (userId) => `/api/sleep/predict/${userId}`));

bindClick('btnKnowledgeRecs', async () => {
  const getVal = (id, fallback) => {
    const el = document.getElementById(id);
    if (!el) return fallback;
    if (el.type === 'number') return Number(el.value) || fallback;
    if (el.type === 'checkbox') return el.checked;
    return el.value || fallback;
  };

  const body = {
    daily_calories: Number(getVal('kbDailyCalories', DEFAULTS.KNOWLEDGE_RECS.DAILY_CALORIES)),
    daily_protein: Number(getVal('kbDailyProtein', DEFAULTS.KNOWLEDGE_RECS.DAILY_PROTEIN)),
    energy_level: Number(getVal('kbEnergyLevel', DEFAULTS.KNOWLEDGE_RECS.ENERGY_LEVEL)),
    sleep_hours: Number(getVal('kbSleepHours', DEFAULTS.KNOWLEDGE_RECS.SLEEP_HOURS)),
    upcoming_difficulty: Number(getVal('kbUpcomingDifficulty', DEFAULTS.KNOWLEDGE_RECS.UPCOMING_DIFFICULTY)),
    recent_session_duration: Number(getVal('kbRecentSessionDuration', DEFAULTS.KNOWLEDGE_RECS.RECENT_SESSION_DURATION)),
    macro_balance: getVal('kbMacroBalance', DEFAULTS.KNOWLEDGE_RECS.MACRO_BALANCE),
    macro_balance_details: {
      protein: getVal('kbMacroProtein', DEFAULTS.KNOWLEDGE_RECS.MACRO_DETAIL),
      carbs: getVal('kbMacroCarbs', DEFAULTS.KNOWLEDGE_RECS.MACRO_DETAIL),
      fat: getVal('kbMacroFat', DEFAULTS.KNOWLEDGE_RECS.MACRO_DETAIL)
    },
    correlation_nutrition_study: Number(getVal('kbCorrelationNutritionStudy', DEFAULTS.KNOWLEDGE_RECS.CORRELATION_NUTRITION)),
    adherence_rate: Number(getVal('kbAdherenceRate', DEFAULTS.KNOWLEDGE_RECS.ADHERENCE_RATE))
  };
  await requestForActiveUser('Knowledge Base Recommendations', (userId) => `/api/recommendations/${userId}`, {
    method: 'POST', body
  });
  showToast('Knowledge recommendations ready.', 'info');
});

bindClick('btnActivityRecs', async () => {
  const n = Number(document.getElementById('activityCount')?.value) || DEFAULTS.ACTIVITY_RECS.COUNT;
  await requestForActiveUser('Activity Recommendations', (userId) => `/api/activity-recommendations/${userId}?n=${n}`);
  showToast('Activity recommendations loaded.', 'info');
});

bindSubmit('activityLogForm', async (form) => {
  const userId = getActiveUserId();
  const body = {
    user_id: userId,
    activity_type: form.elements['activity_type'].value,
    duration_minutes: Number(form.elements['duration_minutes'].value),
    notes: (form.elements['notes'].value || '').trim()
  };
  const energy = Number(form.elements['energy_after'].value);
  if (energy) body.energy_after = energy;
  if (!body.duration_minutes || body.duration_minutes < 1) throw new Error('Duration must be greater than 0.');
  const payload = await apiRequest('/api/activity/log', { method: 'POST', body });
  form.reset();
  showToast('Activity logged.', 'success');
  writeOutput('Activity Logged', payload);
});

bindClick('btnActivityLogs', async () => {
  await requestForActiveUser('Activity Logs', (userId) => `/api/activity/logs/${userId}?limit=50`);
  showToast('Activity logs loaded.', 'info');
});

bindClick('btnActivityTrends', async () => {
  await requestForActiveUser('Activity Trends', (userId) => `/api/activity/trends/${userId}?days=7`);
  showToast('Activity trends ready.', 'info');
});

bindClick('btnScheduleHistory', async () => {
  await requestForActiveUser('Schedule History', (userId) => `/api/schedule/history/${userId}?limit=10`);
  showToast('Schedule history loaded.', 'info');
});

bindClick('btnProductivitySessions', async () => {
  await requestForActiveUser('Productivity Sessions', (userId) => `/api/productivity/sessions/${userId}?limit=10`);
  showToast('Productivity sessions loaded.', 'info');
});

initTabs();
initTaskBuilder();
initCharts();
initQuickActions();
setChatEmptyState();
refreshKpis();
updateAuthStatus();

document.querySelectorAll('[data-auth-mode]').forEach((tab) => {
  const userSection = document.getElementById('section-user');
  const commandDeck = document.querySelector('.command-deck');
  const loginPanel = document.querySelector('.session-login-top');
  const registerPlaceholder = userSection ? document.createComment('registration location') : null;
  if (userSection && registerPlaceholder) userSection.parentNode.insertBefore(registerPlaceholder, userSection);

  tab.addEventListener('click', () => {
    const mode = tab.dataset.authMode;
    document.querySelectorAll('[data-auth-mode]').forEach((item) => {
      item.classList.toggle('active', item.dataset.authMode === mode);
    });
    if (mode === 'register') {
      if (commandDeck && userSection) {
        commandDeck.classList.add('auth-register-mode');
        loginPanel?.setAttribute('hidden', '');
        userSection.classList.remove('tab-hidden');
        commandDeck.appendChild(userSection);
      }
    } else {
      if (commandDeck && userSection && registerPlaceholder) {
        commandDeck.classList.remove('auth-register-mode');
        loginPanel?.removeAttribute('hidden');
        registerPlaceholder.parentNode.insertBefore(userSection, registerPlaceholder.nextSibling);
        userSection.classList.add('tab-hidden');
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });
});

// Refresh trends from persisted data when the time range changes or Refresh is clicked.
window.addEventListener('trends-refresh', () => {
  const userId = getActiveUserId();
  if (userId) loadTrends(userId);
});

// Reload trends whenever the active user changes.
if (activeUserEl) {
  activeUserEl.addEventListener('change', () => {
    const userId = activeUserEl.value.trim();
    if (userId) loadTrends(userId);
  });
}

// Clear output button
document.getElementById('clearOutput')?.addEventListener('click', () => {
  const outputEl = document.getElementById('output');
  if (outputEl) {
    outputEl.innerHTML = '<div class="output-placeholder">Run any action to see the response payload here.</div>';
  }
});

const apiOutputToggle = document.getElementById('toggleApiOutput');
const savedApiOutput = localStorage.getItem('showApiOutput');
if (apiOutputToggle && (savedApiOutput === 'true' || savedApiOutput === 'false')) {
  apiOutputToggle.checked = savedApiOutput === 'true';
  const outputPanel = document.getElementById('outputPanel');
  if (outputPanel) outputPanel.style.display = apiOutputToggle.checked ? '' : 'none';
  document.querySelectorAll('.developer-api-control').forEach((control) => {
    control.style.display = apiOutputToggle.checked ? '' : 'none';
  });
}

apiOutputToggle?.addEventListener('change', (event) => {
  const outputPanel = document.getElementById('outputPanel');
  if (!outputPanel) return;
  outputPanel.style.display = event.target.checked ? '' : 'none';
  document.querySelectorAll('.developer-api-control').forEach((control) => {
    control.style.display = event.target.checked ? '' : 'none';
  });
  localStorage.setItem('showApiOutput', event.target.checked ? 'true' : 'false');
});
window.addEventListener('auth-required', () => {
  setAuthGate(false);
  switchTab('section-user');
  updateAuthStatus();
  showToast('Please log in to continue.', 'error');
});