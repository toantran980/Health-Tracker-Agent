import { trendState } from './state.js';

let caloriesChart, macrosChart, focusChart;

export function timestampLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function capTrendPoints(max = 10) {
  while (trendState.labels.length > max) {
    trendState.labels.shift(); trendState.calories.shift(); trendState.protein.shift();
    trendState.carbs.shift(); trendState.fat.shift();
  }
  while (trendState.focusLabels.length > max) {
    trendState.focusLabels.shift(); trendState.focus.shift();
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
  focusChart.data.labels = trendState.focusLabels;
  focusChart.data.datasets[0].data = trendState.focus;
  focusChart.update('none');
  requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));
  updateTrendsSummary();
}

export function addTrendPoint(values) {
  trendState.labels.push(timestampLabel());
  trendState.calories.push(values.calories ?? null);
  trendState.protein.push(values.protein ?? null);
  trendState.carbs.push(values.carbs ?? null);
  trendState.fat.push(values.fat ?? null);
  trendState.focusLabels.push(timestampLabel());
  trendState.focus.push(values.focus ?? null);
  capTrendPoints();
  updateCharts();
}

export function setTrendData(nutrition, focus) {
  const n = Array.isArray(nutrition) ? nutrition : [];
  const f = Array.isArray(focus) ? focus : [];
  trendState.labels = n.map((p) => p.date);
  trendState.calories = n.map((p) => p.calories ?? null);
  trendState.protein = n.map((p) => p.protein_g ?? null);
  trendState.carbs = n.map((p) => p.carbs_g ?? null);
  trendState.fat = n.map((p) => p.fat_g ?? null);
  trendState.focusLabels = f.map((p) => formatFocusLabel(p.timestamp));
  trendState.focus = f.map((p) => (p.focus != null ? Number(p.focus) : null));
  updateCharts();
}

function formatFocusLabel(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  if (isNaN(d.getTime())) return String(timestamp).slice(0, 10);
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function updateTrendsSummary() {
  const avgCaloriesEl = document.getElementById('trendAvgCalories');
  const avgProteinEl = document.getElementById('trendAvgProtein');
  const avgFocusEl = document.getElementById('trendAvgFocus');
  const dataPointsEl = document.getElementById('trendDataPoints');

  if (avgCaloriesEl) {
    const validCalories = trendState.calories.filter(c => c !== null && c !== undefined);
    const avg = validCalories.length > 0 ? Math.round(validCalories.reduce((a, b) => a + b, 0) / validCalories.length) : '-';
    avgCaloriesEl.textContent = avg !== '-' ? `${avg} kcal` : '-';
  }

  if (avgProteinEl) {
    const validProtein = trendState.protein.filter(p => p !== null && p !== undefined);
    const avg = validProtein.length > 0 ? Math.round(validProtein.reduce((a, b) => a + b, 0) / validProtein.length) : '-';
    avgProteinEl.textContent = avg !== '-' ? `${avg}g` : '-';
  }

  if (avgFocusEl) {
    const validFocus = trendState.focus.filter(f => f !== null && f !== undefined);
    const avg = validFocus.length > 0 ? (validFocus.reduce((a, b) => a + b, 0) / validFocus.length).toFixed(1) : '-';
    avgFocusEl.textContent = avg !== '-' ? `${avg}/10` : '-';
  }

  if (dataPointsEl) {
    const count = trendState.labels.length;
    dataPointsEl.textContent = count;
  }
}

export function initCharts() {
  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 750,
      easing: 'easeInOutQuart'
    },
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20,
          font: {
            size: 12,
            family: "'Space Grotesk', sans-serif"
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(26, 37, 38, 0.95)',
        titleColor: '#e8f4fa',
        bodyColor: '#e8f4fa',
        borderColor: 'rgba(116, 165, 176, 0.3)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
        usePointStyle: true
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        },
        ticks: {
          font: {
            size: 11
          }
        }
      },
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(116, 165, 176, 0.1)'
        },
        ticks: {
          font: {
            size: 11
          }
        }
      }
    }
  };

  const caloriesCanvas = document.getElementById('caloriesChart');
  if (caloriesCanvas) {
    caloriesChart = new Chart(caloriesCanvas, {
      type: 'line',
      data: { 
        labels: [], 
        datasets: [{ 
          label: 'Calories', 
          data: [], 
          borderColor: '#0d8a6f',
          backgroundColor: 'rgba(13, 138, 111, 0.15)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#0d8a6f',
          pointBorderColor: '#fff',
          pointBorderWidth: 2
        }] 
      },
      options: { 
        ...commonOptions, 
        scales: { 
          ...commonOptions.scales,
          y: { 
            ...commonOptions.scales.y,
            beginAtZero: true, 
            suggestedMax: 2500 
          } 
        } 
      }
    });
  }

  const macrosCanvas = document.getElementById('macrosChart');
  if (macrosCanvas) {
    macrosChart = new Chart(macrosCanvas, {
      type: 'line',
      data: { 
        labels: [], 
        datasets: [
          { 
            label: 'Protein', 
            data: [], 
            borderColor: '#0d8a6f',
            backgroundColor: 'rgba(13, 138, 111, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 6
          },
          { 
            label: 'Carbs',   
            data: [], 
            borderColor: '#e07a45',
            backgroundColor: 'rgba(224, 122, 69, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 6
          },
          { 
            label: 'Fat',     
            data: [], 
            borderColor: '#5a7d9e',
            backgroundColor: 'rgba(90, 125, 158, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 6
          }
        ]
      },
      options: { 
        ...commonOptions, 
        scales: { 
          ...commonOptions.scales,
          y: { 
            ...commonOptions.scales.y,
            beginAtZero: true, 
            suggestedMax: 200 
          } 
        } 
      }
    });
  }

  const focusCanvas = document.getElementById('focusChart');
  if (focusCanvas) {
    focusChart = new Chart(focusCanvas, {
      type: 'line',
      data: { 
        labels: [], 
        datasets: [{ 
          label: 'Focus Score', 
          data: [], 
          borderColor: '#e07a45',
          backgroundColor: 'rgba(224, 122, 69, 0.15)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#e07a45',
          pointBorderColor: '#fff',
          pointBorderWidth: 2
        }] 
      },
      options: { 
        ...commonOptions, 
        scales: { 
          ...commonOptions.scales,
          y: { 
            ...commonOptions.scales.y,
            beginAtZero: true, 
            suggestedMax: 10,
            ticks: {
              stepSize: 1
            }
          } 
        } 
      }
    });
  }

  // Initialize time range selector — re-fetch data for the selected window.
  const timeRangeSelect = document.getElementById('trendsTimeRange');
  if (timeRangeSelect) {
    timeRangeSelect.addEventListener('change', () => {
      window.dispatchEvent(new CustomEvent('trends-refresh'));
    });
  }

  // Initialize refresh button — re-fetch latest persisted data.
  const refreshBtn = document.getElementById('refreshTrends');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('trends-refresh'));
    });
  }
}
