/* ── State ────────────────────────────────────────────────── */
let currentBets   = [];
let customSlipLegs = [];

/* ── Sport filter ─────────────────────────────────────────── */
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

/* ── Helpers ──────────────────────────────────────────────── */
function sportClass(sport) {
  return 'sport-' + sport.toLowerCase();
}

function probColor(p) {
  return p >= 78 ? 'var(--success)' : p >= 70 ? 'var(--medium)' : 'var(--danger)';
}

function logoImg(url, cls = 'team-logo') {
  if (!url) return `<span class="logo-placeholder ${cls}"></span>`;
  return `<img src="${url}" class="${cls}" alt="" onerror="this.style.display='none'">`;
}

function kickoffBadge(time) {
  if (!time) return '';
  return `<span class="kickoff-badge ms-1">${time}</span>`;
}

/* ── Run analysis ─────────────────────────────────────────── */
async function runAnalysis() {
  const sport   = document.querySelector('.btn-filter.active').dataset.sport;
  const minProb = document.getElementById('prob-slider').value / 100;
  const stake   = parseFloat(document.getElementById('stake-input').value) || 10;

  setLoading(true);
  try {
    const res  = await fetch(`/api/analyze?sport=${sport}&min_prob=${minProb}&stake=${stake}`);
    const data = await res.json();

    currentBets = data.bets || [];

    document.getElementById('stat-games').textContent = data.total_games;
    document.getElementById('stat-bets').textContent  = data.total_recommended;

    const src = document.getElementById('odds-source');
    if (src) src.textContent = data.real_odds ? '✓ Live bookmaker odds' : 'Estimated odds';

    renderBetsTable(currentBets, data.total_games);
    renderBetCards(currentBets, data.total_games);
    renderSmartSlips(data.smart_slips || [], stake);
    closeDetail();
  } catch (err) {
    console.error(err);
    showToast('Analysis failed — is the server running?', 'danger');
  } finally {
    setLoading(false);
  }
}

/* ── Desktop table ────────────────────────────────────────── */
function renderBetsTable(bets, totalGames) {
  const tbody   = document.getElementById('bets-tbody');
  const noGames = document.getElementById('no-games');
  const noBets  = document.getElementById('no-bets');
  const wrap    = document.getElementById('bets-table-wrap');

  [noGames, noBets].forEach(el => el?.classList.add('d-none'));
  wrap?.classList.add('d-none');

  if (totalGames === 0) { noGames?.classList.remove('d-none'); return; }
  if (!bets.length)     { noBets?.classList.remove('d-none');  return; }
  wrap?.classList.remove('d-none');

  if (!tbody) return;
  tbody.innerHTML = bets.map((b, i) => {
    const pc = probColor(b.probability);
    const evCls = b.expected_value >= 0 ? 'ev-positive' : 'ev-negative';
    const evSign = b.expected_value >= 0 ? '+' : '';
    return `
    <tr onclick="onRowClick(${i})" data-index="${i}">
      <td>
        <div class="d-flex align-items-center gap-1 mb-1">
          ${logoImg(b.home_logo)} <span class="fw-semibold" style="font-size:12px">${b.home}</span>
          ${kickoffBadge(b.kick_off)}
        </div>
        <div class="d-flex align-items-center gap-1">
          ${logoImg(b.away_logo)} <span class="text-muted" style="font-size:12px">${b.away}</span>
        </div>
        ${b.league ? `<div class="text-muted" style="font-size:10px;margin-top:2px">${b.league}${b.surface ? ' · ' + b.surface : ''}</div>` : ''}
      </td>
      <td><span class="badge-sport ${sportClass(b.sport)}">${b.sport}</span></td>
      <td>
        <div class="fw-medium" style="font-size:12px">${b.bet_type}</div>
        <div class="text-muted" style="font-size:11px">${b.side}</div>
      </td>
      <td class="text-center fw-bold text-accent">${b.odds}</td>
      <td>
        <div class="prob-bar-wrap">
          <div class="prob-bar-bg">
            <div class="prob-bar-fill" style="width:${b.probability}%;background:${pc}"></div>
          </div>
          <span class="prob-label" style="color:${pc}">${b.probability}%</span>
        </div>
      </td>
      <td class="text-center ${evCls}">${evSign}${b.expected_value}%</td>
      <td class="text-center"><span class="badge-conf conf-${b.confidence}">${b.confidence}</span></td>
      <td>
        <button class="btn btn-sm py-0 px-2"
          style="background:var(--bg3);border:1px solid var(--border);color:var(--text);font-size:11px"
          onclick="event.stopPropagation();addToCustomSlip(${i})">+</button>
      </td>
    </tr>`;
  }).join('');
}

/* ── Mobile cards ─────────────────────────────────────────── */
function renderBetCards(bets, totalGames) {
  const container = document.getElementById('bets-cards');
  const noGames   = document.getElementById('no-games');
  const noBets    = document.getElementById('no-bets');
  if (!container) return;

  container.innerHTML = '';
  if (totalGames === 0 || !bets.length) return; // already shown by table handler

  container.innerHTML = bets.map((b, i) => {
    const pc     = probColor(b.probability);
    const evSign = b.expected_value >= 0 ? '+' : '';
    const evCls  = b.expected_value >= 0 ? 'ev-positive' : 'ev-negative';
    return `
    <div class="bet-card" data-index="${i}" onclick="onRowClick(${i})">
      <div class="bet-card-header">
        <div class="bet-card-match">
          ${logoImg(b.home_logo)} ${logoImg(b.away_logo)}
          <span class="bet-card-match-name">${b.home} vs ${b.away}</span>
        </div>
        <div class="d-flex gap-1 align-items-center flex-shrink-0">
          ${kickoffBadge(b.kick_off)}
          <span class="badge-sport ${sportClass(b.sport)}">${b.sport}</span>
        </div>
      </div>
      <div class="bet-card-meta">
        <span>${b.bet_type} — ${b.side}</span>
        <span class="badge-conf conf-${b.confidence}">${b.confidence}</span>
      </div>
      <div class="bet-card-stats">
        <div class="bet-stat">
          <div class="bet-stat-label">Odds</div>
          <div class="bet-stat-value text-accent">${b.odds}</div>
        </div>
        <div class="bet-stat">
          <div class="bet-stat-label">Prob</div>
          <div class="bet-stat-value" style="color:${pc}">${b.probability}%</div>
        </div>
        <div class="bet-stat">
          <div class="bet-stat-label">EV</div>
          <div class="bet-stat-value ${evCls}">${evSign}${b.expected_value}%</div>
        </div>
      </div>
      <button class="btn btn-sm w-100 mt-2 py-1"
        style="background:var(--bg3);border:1px solid var(--border);color:var(--text);font-size:11px"
        onclick="event.stopPropagation();addToCustomSlip(${i})">
        + Add to slip
      </button>
    </div>`;
  }).join('');
}

/* ── Row / card click → detail ────────────────────────────── */
function onRowClick(index) {
  document.querySelectorAll('#bets-tbody tr, .bet-card').forEach(r => r.classList.remove('selected'));
  document.querySelector(`[data-index="${index}"]`)?.classList.add('selected');
  showDetail(currentBets[index]);
}

function showDetail(bet) {
  const panel   = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');
  panel.classList.remove('d-none');

  const pc = probColor(bet.probability);
  const evSign = bet.expected_value >= 0 ? '+' : '';

  content.innerHTML = `
    <div class="match-header">
      ${logoImg(bet.home_logo, 'team-logo-lg')}
      <div class="flex-grow-1 min-w-0">
        <div class="fw-bold">${bet.home}</div>
        <div class="text-muted" style="font-size:11px">${bet.league || ''}${bet.surface ? ' · ' + bet.surface : ''}</div>
      </div>
      <span class="match-vs">vs</span>
      <div class="flex-grow-1 min-w-0 text-end">
        <div class="fw-bold">${bet.away}</div>
        ${bet.kick_off ? `<div class="kickoff-badge">${bet.kick_off}</div>` : ''}
      </div>
      ${logoImg(bet.away_logo, 'team-logo-lg')}
    </div>

    <div class="row g-2 mb-3">
      <div class="col-6">
        <div class="bet-stat">
          <div class="bet-stat-label">Bet Type</div>
          <div style="font-size:13px;font-weight:600;margin-top:2px">${bet.bet_type}</div>
          <div class="text-muted" style="font-size:11px">${bet.side}</div>
        </div>
      </div>
      <div class="col-2">
        <div class="bet-stat">
          <div class="bet-stat-label">Odds</div>
          <div class="bet-stat-value text-accent">${bet.odds}</div>
        </div>
      </div>
      <div class="col-2">
        <div class="bet-stat">
          <div class="bet-stat-label">Prob</div>
          <div class="bet-stat-value" style="color:${pc}">${bet.probability}%</div>
        </div>
      </div>
      <div class="col-2">
        <div class="bet-stat">
          <div class="bet-stat-label">EV</div>
          <div class="bet-stat-value ${bet.expected_value >= 0 ? 'ev-positive' : 'ev-negative'}">
            ${evSign}${bet.expected_value}%
          </div>
        </div>
      </div>
    </div>

    <div class="text-muted fw-semibold mb-2" style="font-size:10px;text-transform:uppercase;letter-spacing:.05em">
      <i class="bi bi-cpu me-1"></i>Model Reasoning
    </div>
    ${(bet.reasoning || []).map(r => `
      <div class="reasoning-item">
        <i class="bi bi-dot"></i><span>${r}</span>
      </div>`).join('')}`;
}

function closeDetail() {
  document.getElementById('detail-panel')?.classList.add('d-none');
  document.querySelectorAll('#bets-tbody tr, .bet-card').forEach(r => r.classList.remove('selected'));
}

/* ── Smart slips ──────────────────────────────────────────── */
function renderSmartSlips(slips, stake) {
  const el = document.getElementById('smart-slips');
  if (!slips.length) {
    el.innerHTML = '<p class="text-muted small text-center py-2">No qualifying slips</p>';
    return;
  }
  el.innerHTML = slips.map(slip => {
    const legs = slip.legs.map(leg => `
      <div class="slip-leg">
        <div class="min-w-0">
          <div class="slip-leg-match text-truncate">${leg.home} vs ${leg.away}</div>
          <div style="font-size:10px;color:var(--muted)">${leg.bet_type} — ${leg.side}</div>
        </div>
        <span class="text-accent fw-bold flex-shrink-0">×${leg.odds}</span>
      </div>`).join('');

    const pc = slip.combined_probability >= 60 ? 'var(--success)'
             : slip.combined_probability >= 45 ? 'var(--medium)' : 'var(--danger)';
    return `
    <div class="slip-card">
      <div class="slip-header">
        <span>${slip.label}</span>
        ${slip.legs.length > 1 ? `<span style="color:${pc}">${slip.combined_probability}%</span>` : ''}
      </div>
      ${legs}
      <div class="slip-footer">
        <span class="text-muted">$${slip.stake} @ <strong class="text-accent">${slip.combined_odds}</strong></span>
        <span class="slip-payout">$${slip.potential_payout}</span>
      </div>
    </div>`;
  }).join('');
}

/* ── Custom slip ──────────────────────────────────────────── */
function addToCustomSlip(index) {
  const bet = currentBets[index];
  if (!bet) return;
  const key = `${bet.game_id}_${bet.bet_type}`;
  if (customSlipLegs.find(l => `${l.game_id}_${l.bet_type}` === key)) {
    showToast('Already in slip', 'warning'); return;
  }
  customSlipLegs.push(bet);
  renderCustomSlip();
  showToast(`Added: ${bet.home} vs ${bet.away}`, 'success');
}

function removeFromCustomSlip(i) {
  customSlipLegs.splice(i, 1);
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
    emptyMsg?.classList.remove('d-none');
    ['custom-odds','custom-prob','custom-payout'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '—';
    });
    return;
  }
  emptyMsg?.classList.add('d-none');
  container.innerHTML = customSlipLegs.map((leg, i) => `
    <div class="custom-leg">
      <div class="min-w-0">
        <div class="fw-semibold text-truncate" style="font-size:12px">${leg.home} vs ${leg.away}</div>
        <div class="text-muted" style="font-size:11px">${leg.bet_type} ${leg.side} @ ${leg.odds}</div>
      </div>
      <button class="custom-leg-remove" onclick="removeFromCustomSlip(${i})">×</button>
    </div>`).join('');

  const odds  = customSlipLegs.reduce((a, l) => a * l.odds, 1);
  const prob  = customSlipLegs.reduce((a, l) => a * (l.probability / 100), 1);
  const payout = (stake * odds).toFixed(2);

  document.getElementById('custom-odds').textContent   = odds.toFixed(2);
  document.getElementById('custom-prob').textContent   = (prob * 100).toFixed(1) + '%';
  document.getElementById('custom-payout').textContent = '$' + payout;
}

/* ── Email subscribe ──────────────────────────────────────── */
async function subscribeEmail() {
  const email = document.getElementById('sub-email')?.value?.trim();
  const msg   = document.getElementById('sub-msg');
  if (!email || !msg) return;

  try {
    const res  = await fetch('/subscribe', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    msg.style.color = data.ok ? 'var(--success)' : 'var(--danger)';
    msg.textContent = data.message;
  } catch {
    msg.style.color = 'var(--danger)';
    msg.textContent = 'Failed — try again';
  }
}

/* ── Loading ──────────────────────────────────────────────── */
function setLoading(on) {
  const btn  = document.getElementById('analyze-btn');
  const spin = document.getElementById('loading');
  const wrap = document.getElementById('bets-table-wrap');
  const cards = document.getElementById('bets-cards');

  btn.disabled  = on;
  btn.innerHTML = on
    ? '<span class="spinner-border spinner-border-sm me-1"></span>Analyzing…'
    : '<i class="bi bi-search me-1"></i>Analyze';

  if (on) {
    spin.classList.remove('d-none');
    wrap?.classList.add('d-none');
    if (cards) cards.innerHTML = '';
  } else {
    spin.classList.add('d-none');
  }
}

/* ── Toast ────────────────────────────────────────────────── */
function showToast(msg, type = 'success') {
  const colors = { success: 'var(--success)', danger: 'var(--danger)', warning: 'var(--medium)' };
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:20px;right:16px;z-index:9999;
    background:var(--bg2);border:1px solid ${colors[type]||'var(--border)'};
    border-radius:8px;padding:10px 14px;font-size:13px;color:var(--text);
    box-shadow:0 4px 20px rgba(0,0,0,.4);max-width:300px;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

/* ── Auto-run on load ─────────────────────────────────────── */
window.addEventListener('load', () => setTimeout(runAnalysis, 300));
