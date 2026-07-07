import { trendState } from './state.js';

let caloriesChart, macrosChart, focusChart;

export function timestampLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function capTrendPoints(max = 10) {
  while (trendState.labels.length > max) {
    trendState.labels.shift(); trendState.calories.shift(); trendState.protein.shift();
    trendState.carbs.shift(); trendState.fat.shift(); trendState.focus.shift();
  }
}

export function updateCharts() {
  if (!caloriesChart || !macrosChart || !focusChart) return;
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

export function addTrendPoint(values) {
  trendState.labels.push(timestampLabel());
  trendState.calories.push(values.calories ?? null);
  trendState.protein.push(values.protein ?? null);
  trendState.carbs.push(values.carbs ?? null);
  trendState.fat.push(values.fat ?? null);
  trendState.focus.push(values.focus ?? null);
  capTrendPoints();
  updateCharts();
}

export function initCharts() {
  const commonOptions = {
    responsive: true, maintainAspectRatio: false, animation: false,
    scales: { y: { beginAtZero: true } }
  };

  const caloriesCanvas = document.getElementById('caloriesChart');
  if (caloriesCanvas) {
    caloriesChart = new Chart(caloriesCanvas, {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Calories', data: [], borderColor: '#0f6f5f', backgroundColor: 'rgba(15, 111, 95, 0.2)', tension: 0.25 }] },
      options: { ...commonOptions, scales: { y: { beginAtZero: true, suggestedMax: 2000 } } }
    });
  }

  const macrosCanvas = document.getElementById('macrosChart');
  if (macrosCanvas) {
    macrosChart = new Chart(macrosCanvas, {
      type: 'line',
      data: { labels: [], datasets: [
        { label: 'Protein', data: [], borderColor: '#2b7a4b', tension: 0.25 },
        { label: 'Carbs',   data: [], borderColor: '#c07f2b', tension: 0.25 },
        { label: 'Fat',     data: [], borderColor: '#8c4fa3', tension: 0.25 }
      ]},
      options: { ...commonOptions, scales: { y: { beginAtZero: true, suggestedMax: 200 } } }
    });
  }

  const focusCanvas = document.getElementById('focusChart');
  if (focusCanvas) {
    focusChart = new Chart(focusCanvas, {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Focus Score', data: [], borderColor: '#1f4f8a', backgroundColor: 'rgba(31, 79, 138, 0.2)', tension: 0.25 }] },
      options: { ...commonOptions, scales: { y: { beginAtZero: true, suggestedMax: 10 } } }
    });
  }
}
