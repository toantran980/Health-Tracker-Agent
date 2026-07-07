import { apiBaseEl, activeUserEl } from './dom.js';
import { appMetrics } from './state.js';
import { apiRequest, requestForActiveUser, getActiveUserId } from './api.js';
import { initTabs, setChatEmptyState, refreshKpis, writeOutput, showToast, switchTab, appendChatMessage } from './ui.js';
import { initCharts, addTrendPoint } from './charts.js';
import { initTaskBuilder, collectTasks } from './tasks.js';
import { bindClick, bindSubmit } from './utils.js';
import { DEFAULTS } from './config.js';

const savedBase = localStorage.getItem('apiBase');
const savedUser = localStorage.getItem('activeUserId');
if (apiBaseEl) {
  apiBaseEl.value = savedBase || window.location.origin;
  apiBaseEl.addEventListener('input', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
  apiBaseEl.addEventListener('change', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
}
if (activeUserEl) {
  activeUserEl.value = savedUser || '';
  activeUserEl.addEventListener('input', () => localStorage.setItem('activeUserId', activeUserEl.value.trim()));
  activeUserEl.addEventListener('change', () => localStorage.setItem('activeUserId', activeUserEl.value.trim()));
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

bindClick('btnInsights', async () => {
  await requestForActiveUser('Health Insights', (userId) => `/api/insights/${userId}`);
  showToast('Insights generated.', 'info');
});

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

initTabs();
initTaskBuilder();
initCharts();
initQuickActions();
setChatEmptyState();
refreshKpis();
