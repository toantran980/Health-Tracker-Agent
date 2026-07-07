import { appMetrics } from './state.js';
import { taskListEl, taskSummaryEl } from './dom.js';
import { refreshKpis } from './ui.js';
import { DEFAULTS } from './config.js';

export function createTaskRow(task = {}) {
  const row = document.createElement('div');
  row.className = 'task-row';
  row.innerHTML = `
    <label>Title<input type="text" class="task-title" value="${task.title || ''}" placeholder="Task title"></label>
    <label>Duration<input type="number" class="task-duration" min="1" value="${task.duration_minutes || DEFAULTS.TASK.DURATION_MINUTES}"></label>
    <label>Difficulty<input type="number" class="task-difficulty" min="1" max="10" value="${task.difficulty || DEFAULTS.TASK.DIFFICULTY}"></label>
    <label>Deadline (days)<input type="number" class="task-deadline" min="0" value="${task.deadline_days || DEFAULTS.TASK.DEADLINE_DAYS}"></label>
    <button type="button" class="btn btn-remove-task">Remove</button>
  `;
  row.querySelector('.btn-remove-task').addEventListener('click', () => { row.remove(); updateTaskSummary(); });
  row.querySelectorAll('input').forEach((input) => { input.addEventListener('input', updateTaskSummary); });
  return row;
}

export function updateTaskSummary() {
  if (!taskListEl || !taskSummaryEl) return;
  const tasks = collectTasks(false);
  const totalDuration = tasks.reduce((sum, task) => sum + (task.duration_minutes || 0), 0);
  taskSummaryEl.textContent = `Total tasks: ${tasks.length} | Total duration: ${totalDuration} min`;
  appMetrics.tasksPlanned = tasks.length;
  refreshKpis();
}

export function collectTasks(strict = true) {
  if (!taskListEl) return [];
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

export function initTaskBuilder() {
  const btnAddTask = document.getElementById('btnAddTask');
  if (btnAddTask) {
    btnAddTask.addEventListener('click', () => {
      if (taskListEl) {
        taskListEl.appendChild(createTaskRow());
        updateTaskSummary();
      }
    });
  }
  updateTaskSummary();
}
