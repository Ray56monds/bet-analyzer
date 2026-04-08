/* ── State ────────────────────────────────────────────────── */
let currentBets = [];
let customSlipLegs = [];  // array of bet objects

/* ── Sport filter buttons ─────────────────────────────────── */
document.querySelectorAll('.btn-filter').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

/* ── Probability slider ───────────────────────────────────── */
document.getElementById('prob-slider').addEventListener('input', function () {
  document.getElementById('prob-label').textContent = this.value + '%';
});

/* ── Run analysis ─────────────────────────────────────────── */
async function runAnalysis() {
  const sport     = document.querySelector('.btn-filter.active').dataset.sport;
  const minProb   = document.getElementById('prob-slider').value / 100;
  const stake     = parseFloat(document.getElementById('stake-input').value) || 10;

  setLoading(true);

  try {
    const url = `/api/analyze?sport=${sport}&min_prob=${minProb}&stake=${stake}`;
    const res = await fetch(url);
    const data = await res.json();

    currentBets = data.bets || [];

    document.getElementById('stat-games').textContent = data.total_games;
    document.getElementById('stat-bets').textContent  = data.total_recommended;

    renderBetsTable(currentBets, data.total_games);
    renderSmartSlips(data.smart_slips || [], stake);
    closeDetail();
  } catch (err) {
    console.error(err);
    showToast('Analysis failed. Is the Flask server running?', 'danger');
  } finally {
    setLoading(false);
  }
}

/* ── Render bets table ────────────────────────────────────── */
function renderBetsTable(bets, totalGames) {
  const tbody   = document.getElementById('bets-tbody');
  const noGames = document.getElementById('no-games');
  const noBets  = document.getElementById('no-bets');
  const wrap    = document.getElementById('bets-table-wrap');

  // Hide all states first
  noGames.classList.add('d-none');
  noBets.classList.add('d-none');
  wrap.classList.add('d-none');

  if (totalGames === 0) {
    noGames.classList.remove('d-none');
    return;
  }
  if (!bets.length) {
    noBets.classList.remove('d-none');
    return;
  }
  wrap.classList.remove('d-none');

  tbody.innerHTML = bets.map((b, i) => {
    const probColor = b.probability >= 78 ? 'var(--success)' : b.probability >= 70 ? 'var(--medium)' : 'var(--danger)';
    const evClass   = b.expected_value >= 0 ? 'ev-positive' : 'ev-negative';
    const evSign    = b.expected_value >= 0 ? '+' : '';
    const sportCls  = 'sport-' + b.sport.toLowerCase();
    const confCls   = 'conf-' + b.confidence;

    return `
    <tr onclick="onRowClick(${i})" data-index="${i}">
      <td>
        <div class="fw-semibold">${b.home}</div>
        <div class="text-muted small">vs ${b.away}</div>
        ${b.league ? `<div class="text-muted" style="font-size:10px">${b.league}</div>` : ''}
      </td>
      <td><span class="badge-sport ${sportCls}">${b.sport}</span></td>
      <td>
        <div class="fw-medium">${b.bet_type}</div>
        <div class="text-muted small">${b.side}</div>
      </td>
      <td class="text-center fw-bold">${b.line > 0 ? '+' : ''}${b.line}</td>
      <td class="text-center fw-bold text-accent">${b.odds}</td>
      <td>
        <div class="prob-bar-wrap">
          <div class="prob-bar-bg">
            <div class="prob-bar-fill" style="width:${b.probability}%;background:${probColor}"></div>
          </div>
          <span class="prob-label" style="color:${probColor}">${b.probability}%</span>
        </div>
      </td>
      <td class="text-center ${evClass}">${evSign}${b.expected_value}%</td>
      <td class="text-center"><span class="badge-conf ${confCls}">${b.confidence}</span></td>
      <td class="text-center">
        <button class="btn btn-sm" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);font-size:11px;padding:2px 8px"
                onclick="event.stopPropagation(); addToCustomSlip(${i})">
          + Add
        </button>
      </td>
    </tr>`;
  }).join('');
}

/* ── Row click → detail ───────────────────────────────────── */
function onRowClick(index) {
  document.querySelectorAll('#bets-tbody tr').forEach(r => r.classList.remove('selected'));
  document.querySelector(`#bets-tbody tr[data-index="${index}"]`)?.classList.add('selected');
  showDetail(currentBets[index]);
}

function showDetail(bet) {
  const panel   = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');
  panel.classList.remove('d-none');

  const sportCls = 'sport-' + bet.sport.toLowerCase();
  const probColor = bet.probability >= 78 ? 'var(--success)' : bet.probability >= 70 ? 'var(--medium)' : 'var(--danger)';

  content.innerHTML = `
    <div class="d-flex align-items-start gap-3 mb-3">
      <div>
        <div class="fw-bold fs-6">${bet.home} vs ${bet.away}</div>
        <div class="text-muted small">${bet.league || ''} ${bet.surface ? '· ' + bet.surface : ''}</div>
      </div>
      <span class="badge-sport ${sportCls} ms-auto">${bet.sport}</span>
    </div>
    <div class="row g-3 mb-3">
      <div class="col-4">
        <div class="text-muted small mb-1">Bet Type</div>
        <div class="fw-semibold">${bet.bet_type}</div>
        <div class="text-muted small">${bet.side}</div>
      </div>
      <div class="col-2">
        <div class="text-muted small mb-1">Odds</div>
        <div class="fw-bold text-accent fs-6">${bet.odds}</div>
      </div>
      <div class="col-3">
        <div class="text-muted small mb-1">Probability</div>
        <div class="fw-bold fs-6" style="color:${probColor}">${bet.probability}%</div>
      </div>
      <div class="col-3">
        <div class="text-muted small mb-1">Exp. Value</div>
        <div class="fw-bold ${bet.expected_value >= 0 ? 'ev-positive' : 'ev-negative'} fs-6">
          ${bet.expected_value >= 0 ? '+' : ''}${bet.expected_value}%
        </div>
      </div>
    </div>
    <div class="text-muted small fw-semibold mb-2 text-uppercase" style="letter-spacing:.05em">
      <i class="bi bi-cpu me-1"></i>Model Reasoning
    </div>
    ${(bet.reasoning || []).map(r => `
      <div class="reasoning-item">
        <i class="bi bi-dot"></i>
        <span>${r}</span>
      </div>`).join('')}`;
}

function closeDetail() {
  document.getElementById('detail-panel').classList.add('d-none');
  document.querySelectorAll('#bets-tbody tr').forEach(r => r.classList.remove('selected'));
}

/* ── Smart slips ──────────────────────────────────────────── */
function renderSmartSlips(slips, stake) {
  const el = document.getElementById('smart-slips');
  if (!slips.length) {
    el.innerHTML = '<p class="text-muted small text-center py-3">No qualifying slips built</p>';
    return;
  }

  el.innerHTML = slips.map(slip => {
    const legs = slip.legs.map(leg => `
      <div class="slip-leg">
        <div>
          <span class="slip-leg-match">${leg.home} vs ${leg.away}</span>
          <div class="text-muted" style="font-size:11px">${leg.bet_type} — ${leg.side}</div>
        </div>
        <span class="text-accent fw-bold">×${leg.odds}</span>
      </div>`).join('');

    const probColor = slip.combined_probability >= 60 ? 'var(--success)' : slip.combined_probability >= 45 ? 'var(--medium)' : 'var(--danger)';

    return `
    <div class="slip-card">
      <div class="slip-header">
        <span>${slip.label}</span>
        ${slip.legs.length > 1 ? `<span style="color:${probColor}">${slip.combined_probability}% combined</span>` : ''}
      </div>
      ${legs}
      <div class="slip-footer">
        <span class="text-muted">$${slip.stake} @ <strong class="text-accent">${slip.combined_odds}</strong></span>
        <span class="slip-payout">$${slip.potential_payout}</span>
      </div>
    </div>`;
  }).join('');
}

/* ── Custom slip builder ──────────────────────────────────── */
function addToCustomSlip(index) {
  const bet = currentBets[index];
  if (!bet) return;

  // Avoid duplicate
  const key = `${bet.game_id}_${bet.bet_type}`;
  if (customSlipLegs.find(l => `${l.game_id}_${l.bet_type}` === key)) {
    showToast('Already in slip', 'warning');
    return;
  }

  customSlipLegs.push(bet);
  renderCustomSlip();
  showToast(`Added: ${bet.home} vs ${bet.away} — ${bet.bet_type}`, 'success');
}

function removeFromCustomSlip(index) {
  customSlipLegs.splice(index, 1);
  renderCustomSlip();
}

function clearCustomSlip() {
  customSlipLegs = [];
  renderCustomSlip();
}

function renderCustomSlip() {
  const container = document.getElementById('custom-slip-legs');
  const emptyMsg  = document.getElementById('slip-empty-msg');
  const stake     = parseFloat(document.getElementById('stake-input').value) || 10;

  if (!customSlipLegs.length) {
    container.innerHTML = '';
    emptyMsg.classList.remove('d-none');
    document.getElementById('custom-odds').textContent   = '—';
    document.getElementById('custom-prob').textContent   = '—';
    document.getElementById('custom-payout').textContent = '—';
    return;
  }

  emptyMsg.classList.add('d-none');

  container.innerHTML = customSlipLegs.map((leg, i) => `
    <div class="custom-leg">
      <div>
        <div style="font-size:12px;font-weight:600">${leg.home} vs ${leg.away}</div>
        <div style="font-size:11px;color:var(--muted)">${leg.bet_type} ${leg.side} @ ${leg.odds}</div>
      </div>
      <button class="custom-leg-remove" onclick="removeFromCustomSlip(${i})">×</button>
    </div>`).join('');

  const combinedOdds = customSlipLegs.reduce((acc, l) => acc * l.odds, 1);
  const combinedProb = customSlipLegs.reduce((acc, l) => acc * (l.probability / 100), 1);
  const payout = (stake * combinedOdds).toFixed(2);

  document.getElementById('custom-odds').textContent   = combinedOdds.toFixed(2);
  document.getElementById('custom-prob').textContent   = (combinedProb * 100).toFixed(1) + '%';
  document.getElementById('custom-payout').textContent = '$' + payout;
}

/* ── Loading state ────────────────────────────────────────── */
function setLoading(on) {
  const btn  = document.getElementById('analyze-btn');
  const spin = document.getElementById('loading');
  const wrap = document.getElementById('bets-table-wrap');

  btn.disabled = on;
  btn.innerHTML = on
    ? '<span class="spinner-border spinner-border-sm me-1"></span>Analyzing…'
    : '<i class="bi bi-search me-1"></i>Analyze';

  if (on) {
    spin.classList.remove('d-none');
    wrap.classList.add('d-none');
  } else {
    spin.classList.add('d-none');
  }
}

/* ── Toast ────────────────────────────────────────────────── */
function showToast(msg, type = 'success') {
  const colors = { success: 'var(--success)', danger: 'var(--danger)', warning: 'var(--medium)' };
  const t = document.createElement('div');
  t.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:var(--bg2);border:1px solid ${colors[type] || 'var(--border)'};
    border-radius:8px;padding:10px 16px;font-size:13px;
    color:var(--text);box-shadow:0 4px 20px rgba(0,0,0,.4);
    animation:fadeIn .2s ease;max-width:340px;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

/* ── Auto-run on load ─────────────────────────────────────── */
window.addEventListener('load', () => {
  // Small delay so the page renders first
  setTimeout(runAnalysis, 400);
});
