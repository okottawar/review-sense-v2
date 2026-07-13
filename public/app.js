const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const errorMsg = document.getElementById('errorMsg');
const uploadCard = document.getElementById('uploadCard');
const loadingCard = document.getElementById('loadingCard');
const resultsSection = document.getElementById('results');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

let lastCsvBase64 = null;
let lastFilename = 'analyzed.csv';

const CATEGORY_COLORS = { Low: 'var(--low)', Medium: 'var(--medium)', High: 'var(--high)' };

browseBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) handleFile(e.target.files[0]);
});

['dragenter', 'dragover'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

resetBtn.addEventListener('click', () => {
  resultsSection.hidden = true;
  uploadCard.hidden = false;
  fileInput.value = '';
  hideError();
});

downloadBtn.addEventListener('click', () => {
  if (!lastCsvBase64) return;
  const byteChars = atob(lastCsvBase64);
  const byteNumbers = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i);
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = lastFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.hidden = false;
}

function hideError() {
  errorMsg.hidden = true;
}

async function handleFile(file) {
  hideError();

  if (!file.name.toLowerCase().endsWith('.csv')) {
    showError('Please upload a .csv file.');
    return;
  }

  uploadCard.hidden = true;
  loadingCard.hidden = false;
  resultsSection.hidden = true;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Something went wrong while analyzing the file.');
    }

    lastCsvBase64 = data.processed_csv_base64;
    lastFilename = data.processed_filename || 'analyzed.csv';

    renderResults(data.summary);

    loadingCard.hidden = true;
    resultsSection.hidden = false;
  } catch (err) {
    loadingCard.hidden = true;
    uploadCard.hidden = false;
    showError(err.message || 'Upload failed. Please try again.');
  }
}

function renderResults(summary) {
  // Dataset preview stats
  const datasetStats = document.getElementById('datasetStats');
  datasetStats.innerHTML = `
    ${stat(summary.record_count, 'Records')}
    ${stat(summary.column_count, 'Columns')}
    ${stat(summary.missing_values, 'Missing values')}
  `;

  // Preview table
  const table = document.getElementById('previewTable');
  const rows = summary.preview_rows || [];
  if (rows.length) {
    const cols = Object.keys(rows[0]);
    let html = '<thead><tr>' + cols.map(c => `<th>${escapeHtml(c)}</th>`).join('') + '</tr></thead>';
    html += '<tbody>' + rows.map(r =>
      '<tr>' + cols.map(c => `<td>${escapeHtml(String(r[c]))}</td>`).join('') + '</tr>'
    ).join('') + '</tbody>';
    table.innerHTML = html;
  }

  // Result stats
  const resultStats = document.getElementById('resultStats');
  resultStats.innerHTML = `
    ${stat(summary.average_satisfaction_score, 'Avg. satisfaction score')}
    ${stat(summary.satisfaction_distribution.High, 'High satisfaction')}
    ${stat(summary.satisfaction_distribution.Low, 'Low satisfaction')}
  `;

  // Distribution bars
  const distBars = document.getElementById('distBars');
  const pct = summary.satisfaction_distribution_pct;
  distBars.innerHTML = ['Low', 'Medium', 'High'].map(cat => `
    <div class="dist-row">
      <span class="dist-label">${cat}</span>
      <div class="dist-track">
        <div class="dist-fill" style="width:${pct[cat]}%; background:${CATEGORY_COLORS[cat]}"></div>
      </div>
      <span class="dist-pct">${pct[cat]}%</span>
    </div>
  `).join('');

  // Insights
  const insightsList = document.getElementById('insightsList');
  insightsList.innerHTML = (summary.insights || []).map(i => `<li>${escapeHtml(i)}</li>`).join('');

  // Rules
  const rulesList = document.getElementById('rulesList');
  rulesList.innerHTML = (summary.top_fired_rules || []).map(r =>
    `<li>${escapeHtml(r.rule)} <strong>(${r.count}&times;)</strong></li>`
  ).join('') || '<li>No rules fired.</li>';
}

function stat(value, label) {
  return `<div class="stat"><span class="stat-value">${value}</span><span class="stat-label">${label}</span></div>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
