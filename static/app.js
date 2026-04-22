const outputEl = document.getElementById('output');
const apiBaseEl = document.getElementById('apiBase');
const activeUserEl = document.getElementById('activeUserId');
const healthStatusEl = document.getElementById('healthStatus');
const taskListEl = document.getElementById('taskList');
const taskSummaryEl = document.getElementById('taskSummary');

const savedBase = localStorage.getItem('apiBase');
const savedUser = localStorage.getItem('activeUserId');
apiBaseEl.value = savedBase || window.location.origin;
activeUserEl.value = savedUser || '';

apiBaseEl.addEventListener('change', () => localStorage.setItem('apiBase', apiBaseEl.value.trim()));
activeUserEl.addEventListener('change', () => localStorage.setItem('activeUserId', activeUserEl.value.trim()));

function writeOutput(title, data) {
  outputEl.textContent = `${title}\n\n${JSON.stringify(data, null, 2)}`;
}

function getApiBase() {
  return apiBaseEl.value.trim().replace(/\/$/, '');
}

function getActiveUserId() {
  const userId = activeUserEl.value.trim();
  if (!userId) {
    throw new Error('Active User ID is required for this action.');
  }
  return userId;
}

async function apiRequest(path, options = {}) {
  const url = `${getApiBase()}${path}`;
  const config = {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  };

  if (options.body !== undefined) {
    config.body = JSON.stringify(options.body);
  }

  const res = await fetch(url, config);
  let payload;
  try {
    payload = await res.json();
  } catch {
    payload = { raw: await res.text() };
  }

  if (!res.ok) {
    const msg = payload && payload.error ? payload.error : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

function safeHandler(handler) {
  return async (event) => {
    if (event) {
      event.preventDefault();
    }
    try {
      await handler(event);
    } catch (err) {
      writeOutput('Error', { message: err.message || 'Unknown error' });
    }
  };
}

function bindClick(id, handler) {
  document.getElementById(id).addEventListener('click', safeHandler(handler));
}

function bindSubmit(id, handler) {
  document.getElementById(id).addEventListener('submit', safeHandler(async (event) => {
    await handler(event.target);
  }));
}

async function requestForActiveUser(title, pathFactory, options = {}) {
  const userId = getActiveUserId();
  const payload = await apiRequest(pathFactory(userId), options);
  writeOutput(title, payload);
  return payload;
}

const trendState = {
  labels: [],
  calories: [],
  protein: [],
  carbs: [],
  fat: [],
  focus: []
};

let caloriesChart;
let macrosChart;
let focusChart;

function timestampLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function capTrendPoints(max = 10) {
  while (trendState.labels.length > max) {
    trendState.labels.shift();
    trendState.calories.shift();
    trendState.protein.shift();
    trendState.carbs.shift();
    trendState.fat.shift();
    trendState.focus.shift();
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

  // Keep the viewport stable while Chart.js redraws canvases.
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
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: { y: { beginAtZero: true } }
  };

  caloriesChart = new Chart(document.getElementById('caloriesChart'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Calories',
        data: [],
        borderColor: '#0f6f5f',
        backgroundColor: 'rgba(15, 111, 95, 0.2)',
        tension: 0.25
      }]
    },
    options: commonOptions
  });

  macrosChart = new Chart(document.getElementById('macrosChart'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Protein', data: [], borderColor: '#2b7a4b', tension: 0.25 },
        { label: 'Carbs', data: [], borderColor: '#c07f2b', tension: 0.25 },
        { label: 'Fat', data: [], borderColor: '#8c4fa3', tension: 0.25 }
      ]
    },
    options: commonOptions
  });

  focusChart = new Chart(document.getElementById('focusChart'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Focus Score',
        data: [],
        borderColor: '#1f4f8a',
        backgroundColor: 'rgba(31, 79, 138, 0.2)',
        tension: 0.25
      }]
    },
    options: {
      ...commonOptions,
      scales: {
        y: {
          beginAtZero: true,
          suggestedMax: 10
        }
      }
    }
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

  row.querySelector('.btn-remove-task').addEventListener('click', () => {
    row.remove();
    updateTaskSummary();
  });

  row.querySelectorAll('input').forEach((input) => {
    input.addEventListener('input', updateTaskSummary);
  });

  return row;
}

function updateTaskSummary() {
  const tasks = collectTasks(false);
  const totalDuration = tasks.reduce((sum, task) => sum + (task.duration_minutes || 0), 0);
  taskSummaryEl.textContent = `Total tasks: ${tasks.length} | Total duration: ${totalDuration} min`;
}

function collectTasks(strict = true) {
  const rows = Array.from(taskListEl.querySelectorAll('.task-row'));
  const tasks = rows.map((row) => {
    const title = row.querySelector('.task-title').value.trim();
    const duration = Number(row.querySelector('.task-duration').value);
    const difficulty = Number(row.querySelector('.task-difficulty').value);
    const deadline = Number(row.querySelector('.task-deadline').value);
    return {
      title,
      duration_minutes: duration,
      difficulty,
      deadline_days: deadline
    };
  });

  if (!strict) {
    return tasks.filter((task) => task.title || task.duration_minutes || task.difficulty || task.deadline_days);
  }

  if (tasks.length === 0) {
    throw new Error('Add at least one task before optimizing.');
  }

  tasks.forEach((task, index) => {
    if (!task.title) {
      throw new Error(`Task ${index + 1}: title is required.`);
    }
    if (!Number.isFinite(task.duration_minutes) || task.duration_minutes <= 0) {
      throw new Error(`Task ${index + 1}: duration must be greater than 0.`);
    }
    if (!Number.isFinite(task.difficulty) || task.difficulty < 1 || task.difficulty > 10) {
      throw new Error(`Task ${index + 1}: difficulty must be between 1 and 10.`);
    }
    if (!Number.isFinite(task.deadline_days) || task.deadline_days < 0) {
      throw new Error(`Task ${index + 1}: deadline days must be 0 or more.`);
    }
  });

  return tasks;
}

function initTaskBuilder() {
  document.getElementById('btnAddTask').addEventListener('click', () => {
    taskListEl.appendChild(createTaskRow());
    updateTaskSummary();
  });

  taskListEl.appendChild(createTaskRow({ title: 'Math Revision', duration_minutes: 90, difficulty: 7, deadline_days: 2 }));
  taskListEl.appendChild(createTaskRow({ title: 'Essay Draft', duration_minutes: 60, difficulty: 6, deadline_days: 1 }));
  updateTaskSummary();
}

bindClick('btnHealth', async () => {
  const payload = await apiRequest('/api/health');
  healthStatusEl.textContent = payload.status || 'ok';
  writeOutput('Health Check', payload);
});

bindSubmit('createUserForm', async (form) => {
  const data = new FormData(form);
  const body = {
    name: data.get('name'),
    age: Number(data.get('age')),
    biological_sex: data.get('biological_sex'),
    weight_kg: Number(data.get('weight_kg')),
    height_cm: Number(data.get('height_cm')),
    goals: [data.get('goal')],
    target_calories: Number(data.get('target_calories')),
    target_protein_g: Number(data.get('target_protein_g')),
    target_carbs_g: Number(data.get('target_carbs_g')),
    target_fat_g: Number(data.get('target_fat_g'))
  };

  const payload = await apiRequest('/api/user/create', { method: 'POST', body });
  if (payload.user && payload.user.user_id) {
    activeUserEl.value = payload.user.user_id;
    localStorage.setItem('activeUserId', payload.user.user_id);
  }
  writeOutput('User Created', payload);
});

bindClick('btnGetUser', async () => {
  await requestForActiveUser('User Profile', (userId) => `/api/user/${userId}`);
});

bindSubmit('mealForm', async (form) => {
  const userId = getActiveUserId();
  const data = new FormData(form);

  const body = {
    meal_type: data.get('meal_type'),
    food_items: [
      {
        name: data.get('food_name'),
        calories: Number(data.get('calories')),
        protein_g: Number(data.get('protein_g')),
        carbs_g: Number(data.get('carbs_g')),
        fat_g: Number(data.get('fat_g'))
      }
    ]
  };

  const payload = await apiRequest(`/api/nutrition/log-meal/${userId}`, { method: 'POST', body });
  if (payload.nutrition) {
    addTrendPoint({
      calories: payload.nutrition.calories,
      protein: payload.nutrition.protein_g,
      carbs: payload.nutrition.carbs_g,
      fat: payload.nutrition.fat_g
    });
  }
  writeOutput('Meal Logged', payload);
});

bindClick('btnAnalyze', async () => {
  await requestForActiveUser('Nutrition Analysis', (userId) => `/api/nutrition/analysis/${userId}`);
});

bindClick('btnMacroRecs', async () => {
  await requestForActiveUser('Macro Recommendations', (userId) => `/api/nutrition/recommendations/${userId}`);
});

bindSubmit('mealRecForm', async (form) => {
  const userId = getActiveUserId();
  const data = new FormData(form);
  const params = new URLSearchParams({
    target_calories: String(Number(data.get('target_calories'))),
    target_protein: String(Number(data.get('target_protein'))),
    mode: data.get('mode'),
    n: String(Number(data.get('n')))
  });
  const payload = await apiRequest(`/api/nutrition/meal-recommendations/${userId}?${params.toString()}`);
  writeOutput('Meal Recommendations', payload);
});

bindSubmit('scheduleForm', async () => {
  const tasks = collectTasks(true);
  await requestForActiveUser('Optimized Schedule', (userId) => `/api/schedule/optimize/${userId}`, {
    method: 'POST',
    body: { tasks }
  });
});

bindClick('btnSlots', async () => {
  await requestForActiveUser('Available Slots', (userId) => `/api/schedule/available-slots/${userId}?duration_minutes=60`);
});

bindSubmit('productivityForm', async (form) => {
  const userId = getActiveUserId();
  const data = new FormData(form);

  const body = {
    hour_of_day: Number(data.get('hour_of_day')),
    day_of_week: Number(data.get('day_of_week')),
    sleep_quality: Number(data.get('sleep_quality')),
    sleep_hours: Number(data.get('sleep_hours')),
    nutrition_score: Number(data.get('nutrition_score')),
    energy_level: Number(data.get('energy_level')),
    previous_session_duration: Number(data.get('previous_session_duration')),
    task_difficulty: Number(data.get('task_difficulty'))
  };

  const payload = await apiRequest(`/api/productivity/predict/${userId}`, { method: 'POST', body });
  if (payload.predicted_focus_score !== undefined) {
    addTrendPoint({ focus: payload.predicted_focus_score });
  }
  writeOutput('Productivity Prediction', payload);
});

bindClick('btnOptimalTime', async () => {
  await requestForActiveUser('Optimal Study Time', (userId) => `/api/productivity/optimal-time/${userId}`);
});

bindSubmit('chatForm', async (form) => {
  const userId = getActiveUserId();
  const data = new FormData(form);
  const body = {
    message: data.get('message')
  };
  const payload = await apiRequest(`/api/chat/${userId}`, { method: 'POST', body });
  writeOutput('Chatbot Reply', payload);
});

bindClick('btnResetChat', async () => {
  await requestForActiveUser('Chatbot Reset', (userId) => `/api/chat/${userId}/reset`, { method: 'POST' });
});

bindClick('btnInsights', async () => {
  await requestForActiveUser('Health Insights', (userId) => `/api/insights/${userId}`);
});

bindClick('btnKnowledgeRecs', async () => {
  const body = {
    daily_calories: 2000,
    daily_protein: 130,
    energy_level: 7,
    sleep_hours: 7.5,
    upcoming_difficulty: 6,
    recent_session_duration: 60,
    macro_balance: 'balanced',
    macro_balance_details: { protein: 'ok', carbs: 'ok', fat: 'ok' },
    correlation_nutrition_study: 0.4,
    adherence_rate: 0.7
  };
  await requestForActiveUser('Knowledge Base Recommendations', (userId) => `/api/recommendations/${userId}`, {
    method: 'POST',
    body
  });
});

// Trigger an initial health check so the user immediately sees server status.
initTaskBuilder();
initCharts();
document.getElementById('btnHealth').click();
