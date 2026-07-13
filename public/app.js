const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const errorMsg = document.getElementById('errorMsg');
const uploadCard = document.getElementById('uploadCard');
const loadingCard = document.getElementById('loadingCard');
const loadingText = document.querySelector('#loadingCard p');
const resultsSection = document.getElementById('results');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

const CHUNK_ROWS = 20000; // rows per request, keeps payload well under 4.5MB
const CATEGORY_COLORS = { Low: 'var(--low)', Medium: 'var(--medium)', High: 'var(--high)' };

let lastRows = null;
let lastFilename = 'analyzed.csv';

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
  if (!lastRows || !lastRows.length) return;
  const cols = Object.keys(lastRows[0]);
  const csvLines = [cols.join(',')];
  for (const row of lastRows) {
    csvLines.push(cols.map(c => csvEscape(row[c])).join(','));
  }
  const blob = new Blob([csvLines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = lastFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

function csvEscape(val) {
  const s = val === null || val === undefined ? '' : String(val);
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.hidden = false;
}

function hideError() {
  errorMsg.hidden = true;
}

function setLoadingText(msg) {
  if (loadingText) loadingText.textContent = msg;
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
  setLoadingText('Parsing CSV in your browser…');

  try {
    const { header, rows } = await parseCsvFile(file);
    await processInChunks(header, rows, file.name);
  } catch (err) {
    loadingCard.hidden = true;
    uploadCard.hidden = false;
    showError(err.message || 'Upload failed. Please try again.');
  }
}

function parseCsvFile(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (!results.data.length) {
          reject(new Error('CSV file contains no data rows.'));
          return;
        }
        resolve({ header: results.meta.fields, rows: results.data });
      },
      error: (err) => reject(new Error('Could not parse CSV: ' + err.message)),
    });
  });
}

async function processInChunks(header, rows, filename) {
  const total = rows.length;
  const chunkCount = Math.ceil(total / CHUNK_ROWS);

  let allResultRows = [];
  let totalMissingValues = 0;
  let columnCount = header.length;
  const ruleHitTotals = {};

  for (let i = 0; i < chunkCount; i++) {
    const start = i * CHUNK_ROWS;
    const end = Math.min(start + CHUNK_ROWS, total);
    const chunkRows = rows.slice(start, end);

    setLoadingText(`Analyzing rows ${start + 1}-${end} of ${total}…`);

    const payload = { header, rows: chunkRows };

    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `Failed processing chunk ${i + 1}/${chunkCount}`);
    }

    allResultRows = allResultRows.concat(data.rows);
    totalMissingValues += data.missing_values || 0;
    columnCount = data.column_count || columnCount;

    for (const [rule, count] of Object.entries(data.rule_hits || {})) {
      ruleHitTotals[rule] = (ruleHitTotals[rule] || 0) + count;
    }
  }

  const summary = buildSummary(allResultRows, totalMissingValues, columnCount, ruleHitTotals);

  lastRows = allResultRows;
  lastFilename = `analyzed_${filename}`;

  renderResults(summary);
  loadingCard.hidden = true;
  resultsSection.hidden = false;
}

function buildSummary(rows, missingValues, columnCount, ruleHitTotals) {
  const total = rows.length || 1;
  const distribution = { Low: 0, Medium: 0, High: 0 };
  let scoreSum = 0;

  for (const row of rows) {
    distribution[row.satisfaction_category] = (distribution[row.satisfaction_category] || 0) + 1;
    scoreSum += Number(row.satisfaction_score) || 0;
  }

  const avg = scoreSum / total;

  const pct = {};
  for (const cat of ['Low', 'Medium', 'High']) {
    pct[cat] = Math.round((distribution[cat] / total) * 1000) / 10;
  }

  const topRules = Object.entries(ruleHitTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([rule, count]) => ({ rule, count }));

  const insights = generateInsights(distribution, total, avg);

  return {
    record_count: rows.length,
    column_count: columnCount,
    missing_values: missingValues,
    average_satisfaction_score: Math.round(avg * 100) / 100,
    satisfaction_distribution: distribution,
    satisfaction_distribution_pct: pct,
    top_fired_rules: topRules,
    preview_rows: rows.slice(0, 5),
    insights,
  };
}

function generateInsights(distribution, total, avg) {
  const insights = [];
  const lowPct = (distribution.Low / total) * 100;
  const highPct = (distribution.High / total) * 100;

  if (highPct >= 60) {
    insights.push(`The majority of reviews (${highPct.toFixed(1)}%) reflect high satisfaction, suggesting strong overall product perception.`);
  }
  if (lowPct >= 30) {
    insights.push(`A notable share of reviews (${lowPct.toFixed(1)}%) fall into the low satisfaction band, worth investigating for recurring complaints.`);
  }
  if (avg >= 70) {
    insights.push(`Average satisfaction score is ${avg.toFixed(1)}/100, indicating generally positive reception.`);
  } else if (avg <= 40) {
    insights.push(`Average satisfaction score is ${avg.toFixed(1)}/100, indicating widespread dissatisfaction.`);
  } else {
    insights.push(`Average satisfaction score is ${avg.toFixed(1)}/100, indicating mixed sentiment overall.`);
  }

  if (!insights.length) {
    insights.push('Satisfaction scores are broadly distributed across categories with no dominant trend.');
  }

  return insights;
}

function renderResults(summary) {
  const datasetStats = document.getElementById('datasetStats');
  datasetStats.innerHTML = `
    ${stat(summary.record_count, 'Records')}
    ${stat(summary.column_count, 'Columns')}
    ${stat(summary.missing_values, 'Missing values')}
  `;

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

  const resultStats = document.getElementById('resultStats');
  resultStats.innerHTML = `
    ${stat(summary.average_satisfaction_score, 'Avg. satisfaction score')}
    ${stat(summary.satisfaction_distribution.High, 'High satisfaction')}
    ${stat(summary.satisfaction_distribution.Low, 'Low satisfaction')}
  `;

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

  const insightsList = document.getElementById('insightsList');
  insightsList.innerHTML = (summary.insights || []).map(i => `<li>${escapeHtml(i)}</li>`).join('');

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
