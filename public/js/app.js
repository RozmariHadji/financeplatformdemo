/* ═══════════════════════════════════════════════════
   GEWiz · app.js
   ═══════════════════════════════════════════════════ */

// ── Formatters ────────────────────────────────────
const eur = n => n == null ? '—' :
  new Intl.NumberFormat('en-IE', { style:'currency', currency:'EUR', maximumFractionDigits:0 }).format(n);

const shortEur = n => {
  if (n == null) return '—';
  const s = n < 0 ? '-' : '', a = Math.abs(n);
  if (a >= 1_000_000) return s + '€' + (a/1_000_000).toFixed(1) + 'm';
  if (a >= 1_000)     return s + '€' + (a/1_000).toFixed(0) + 'k';
  return eur(n);
};

const fmt_pct = n => n == null ? '—' : (n > 0 ? '+' : '') + n.toFixed(1) + '%';

const varCls = (n, type) => {
  if (n == null) return '';
  return (type === 'revenue' ? n > 0 : n < 0) ? 'fav' : 'adv';
};

// ── State ─────────────────────────────────────────
const S = {
  school:    'group',
  city:      'all',
  date:      'ytd',
  version:   'ongoing_rolling',
  filterMonth: null,
  tab:       'dashboard',
  charts:    {},
  dashCache: {},
  fpnaCache: {},
  varCache:  {},
};

// ── Default assumptions ───────────────────────────
const DEF_REGIONS = [
  { id:'aes_nicosia', name:'Alpha English School Nicosia', headcount:650, segment:'Secondary', revenue_per_head:4500, city: 'Nicosia' },
  { id:'aps_nicosia', name:'Alpha Primary School Nicosia', headcount:480, segment:'Primary', revenue_per_head:4500, city: 'Nicosia' },
  { id:'aes_limassol', name:'Alpha English School Limassol', headcount:820, segment:'Secondary', revenue_per_head:4500, city: 'Limassol' },
  { id:'aes_larnaca', name:'Alpha English School Larnaca', headcount:520, segment:'Secondary', revenue_per_head:4500, city: 'Larnaca' },
];
const DEF_RATIOS = {
  direct_labor:0.45, indirect_labor:0.15, management:0.08,
  facilities:0.08, admin:0.06, software:0.04, other_costs:0.03,
};
const RATIO_LABELS = {
  direct_labor:'Direct Labor', indirect_labor:'Indirect Labor',
  management:'Management & Execs', facilities:'Facilities & Utilities',
  admin:'Admin & Overhead', software:'Software & Tools', other_costs:'Other Costs',
};

S.inputSchools = DEF_REGIONS.map(s => ({...s}));
S.inputRatios  = {...DEF_RATIOS};

// ── AI chip helpers ───────────────────────────────
function insight(actual, budget, type) {
  if (!budget || actual == null) return { text:'No comparison available', cls:'neu' };
  const p = (actual - budget) / Math.abs(budget) * 100;
  const fav = type === 'revenue' ? p > 0 : p < 0;
  const a   = Math.abs(p).toFixed(1);
  if (Math.abs(p) < 1.5) return { text:'Tracking in line with budget', cls:'neu' };
  if (fav && Math.abs(p) >= 6) return { text:`${a}% ahead of budget — strong performance`, cls:'pos' };
  if (fav)                     return { text:`${a}% favourable variance`, cls:'pos' };
  if (Math.abs(p) >= 8)        return { text:`${a}% adverse — review recommended`, cls:'neg' };
  return { text:`${a}% adverse variance — monitor`, cls:'neg' };
}

function surInsight(sa, sb) {
  if (sb == null) return { text:'No comparison available', cls:'neu' };
  const v = sa - sb, a = Math.abs(v);
  if (a < 500)  return { text:'Net position on budget', cls:'neu' };
  if (v > 0)    return { text:`€${(a/1000).toFixed(0)}k ahead of budget`, cls:'pos' };
  return { text:`€${(a/1000).toFixed(0)}k behind budget — action may be required`, cls:'neg' };
}

function chip(ins) {
  return `<div class="kpi-ai"><span class="kpi-ai-star">✦</span><span>${ins.text}</span></div>`;
}

function delta(actual, budget, type) {
  if (!budget || actual == null) return '';
  const p = (actual - budget) / Math.abs(budget) * 100;
  const fav = type === 'revenue' ? p > 0 : p < 0;
  const cls = Math.abs(p) < 1.5 ? 'neu' : (fav ? 'pos' : 'neg');
  return `<div class="kpi-delta ${cls}">${p > 0 ? '+' : ''}${p.toFixed(1)}% vs budget</div>`;
}

// ── Fetch ─────────────────────────────────────────
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

// ── Navigation ────────────────────────────────────
const TITLES = { dashboard:'Dashboard', input:'Data Input', fpna:'FP&A Engine', ai:'AI Insights' };

function switchTab(tab) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
  document.getElementById('topbar-title').textContent = TITLES[tab];
  S.tab = tab;

  if (tab === 'dashboard' && !S.dashCache[S.school]) loadDashboard(S.school);
  if (tab === 'fpna'      && !S.fpnaCache[S.school])  loadFpna(S.school);
  if (tab === 'ai'        && !S.varCache[S.school])   loadAi(S.school);
  if (tab === 'input')                                 renderInput();
}



function onVersionChange(v) {
  S.version = v;
  S.dashCache = {}; S.fpnaCache = {}; S.varCache = {}; // invalidate caches
  if (S.version === 'initial_budget' || S.version === '5_year') { S.date = 'full'; document.getElementById('date-select').value='full'; document.getElementById('date-select').disabled=true; } 
  else { document.getElementById('date-select').disabled=false; }
  
  if (S.tab === 'dashboard') loadDashboard(S.school);
  if (S.tab === 'fpna')      loadFpna(S.school);
  if (S.tab === 'ai')        loadAi(S.school);
}

function onCityChange(v) {
  S.city = v;
  S.dashCache = {}; S.fpnaCache = {}; S.varCache = {}; // invalidate caches
  if (S.tab === 'dashboard') loadDashboard(S.school);
  if (S.tab === 'fpna')      loadFpna(S.school);
  if (S.tab === 'ai')        loadAi(S.school);
}
function onDateChange(v) {
  S.date = v;
  // Just trigger re-render from cache
  if (S.tab === 'dashboard' && S.dashCache[S.school]) renderDashboard(S.dashCache[S.school].fpna, S.dashCache[S.school].schools);
  if (S.tab === 'fpna' && S.fpnaCache[S.school]) renderFpna(S.fpnaCache[S.school]);
}


function onChartClick(e, chart, type) {
  const elems = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
  if (!elems.length) {
    if (S.filterMonth !== null) { S.filterMonth = null; onDateChange(S.date); }
    return;
  }
  const idx = elems[0].index;
  if (S.filterMonth === idx) S.filterMonth = null;
  else S.filterMonth = idx;
  onDateChange(S.date);
}
function onSchoolChange(v) {
  S.school = v;
  if (S.tab === 'dashboard') loadDashboard(v);
  if (S.tab === 'fpna')      loadFpna(v);
  if (S.tab === 'ai')        loadAi(v);
}

// ════════════════════════════════════════════════
// DASHBOARD
// ════════════════════════════════════════════════
async function loadDashboard(sid) {
  show('dash-loading'); hide('dash-content');
  try {
    const [fpna, schools] = await Promise.all([
      api(`/api/fpna/${sid}?city=${S.city}&version=${S.version}`),
      api(`/api/schools?city=${S.city}&version=${S.version}`),
    ]);
    S.dashCache[sid] = { fpna, schools };
    renderDashboard(fpna, schools.schools);
  } catch(e) { el('dash-loading').textContent = '⚠ ' + e.message; }
}

function renderDashboard(fpna, schools) {
  let { months, actual_months:AM, categories } = fpna;
  let max_months = (S.date === 'ytd' && AM > 0) ? AM : months.length;

  // Totals
  let revB=0, revA=0, expB=0, expA=0;
  categories.forEach(c => {
    const bS = S.filterMonth !== null ? (c.budget[S.filterMonth]||0) : c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const aS = S.filterMonth !== null ? (c.actual[S.filterMonth]||0) : c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);
    if (c.type==='revenue') { revB+=bS; revA+=aS; }
    else                    { expB+=bS; expA+=aS; }
  });
  const surpA=revA-expA, surpB=revB-expB;
  const totalHeadcount = schools.reduce((s,x)=>s+x.headcount,0);

  // KPIs
  const insRev  = insight(revA, revB, 'revenue');
  const insExp  = insight(expA, expB, 'expenditure');
  const insSurp = surInsight(surpA, surpB);

  el('dash-kpis').innerHTML = `
    <div class="kpi-card ${revA>=revB?'green':'amber'}">
      <div class="kpi-label">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Revenue</div>
      <div class="kpi-value">${shortEur(revA)}</div>
      <div class="kpi-sub">Budget: ${shortEur(revB)}</div>
      ${delta(revA,revB,'revenue')}
    </div>
    <div class="kpi-card ${expA<=expB?'green':'amber'}">
      <div class="kpi-label">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Expenditure</div>
      <div class="kpi-value">${shortEur(expA)}</div>
      <div class="kpi-sub">Budget: ${shortEur(expB)}</div>
      ${delta(expA,expB,'expenditure')}
    </div>
    <div class="kpi-card ${surpA>=surpB?'green':'red'}">
      <div class="kpi-label">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Surplus</div>
      <div class="kpi-value">${shortEur(surpA)}</div>
      <div class="kpi-sub">Budget: ${shortEur(surpB)}</div>
      ${delta(surpA,surpB,'revenue')}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Headcount</div>
      <div class="kpi-value">${totalHeadcount.toLocaleString()}</div>
      <div class="kpi-sub">Across ${schools.length} schools</div>
    </div>`;

  // AI insight strip
  const stripEl = document.getElementById('dash-ai-strip');
  if (stripEl) {
    const items = [
      { ins: insRev,  label: 'Revenue' },
      { ins: insExp,  label: 'Expenditure' },
      { ins: insSurp, label: 'Net surplus' },
      { ins: {text:'Headcount numbers stable — Core revenue secured', cls:'pos'}, label:'Headcount' },
    ];
    stripEl.innerHTML = `<span class="ai-strip-star">✦</span>
      <div class="ai-strip-items">${items.map((x,i)=>`
        ${i>0?'<span class="ai-strip-sep">·</span>':''}
        <span class="ai-strip-item ${x.ins.cls}"><strong>${x.label}:</strong> ${x.ins.text}</span>
      `).join('')}</div>`;
  }

  // Charts
  Object.values(S.charts).forEach(c => { try{c.destroy();}catch(e){} });
  S.charts = {};

  const CF = { family:"'Inter',sans-serif", size:11 };
  const baseScales = {
    x: { grid:{color:'rgba(0,0,0,0.04)'}, ticks:{font:CF} },
    y: { grid:{color:'rgba(0,0,0,0.04)'}, ticks:{font:CF, callback:v=>'€'+(Math.abs(v)>=1000?Math.round(v/1000)+'k':v)} },
  };
  const baseLegend = { labels:{font:CF, padding:14, usePointStyle:true, pointStyleWidth:8} };

  // 1. Revenue line
  const core_revC  = categories.find(c=>c.key==='core_revenue');
  const othC  = categories.find(c=>c.key==='other_income');
  const rBudg = months.map((_,i)=>(core_revC?.budget[i]||0)+(othC?.budget[i]||0));
  const rAct  = months.map((_,i)=>i<max_months ? (core_revC?.actual[i]||0)+(othC?.actual[i]||0) : null);
  const rFcst = months.map((_,i)=>AM>0 && i>=AM? (core_revC?.forecast[i]||0)+(othC?.forecast[i]||0): null);

  S.charts.rev = new Chart(el('chart-revenue'), {
    type:'line',
    data:{ labels:months, datasets:[
      {label:'Budget',   data:rBudg, borderColor:'#334155', borderDash:[4,3], borderWidth:1.5, pointRadius:2, fill:false, tension:.35},
      {label:'Actual',   data:rAct,  borderColor:'#009A3D', backgroundColor:'rgba(0,154,61,.1)', borderWidth:2, pointRadius:3, fill:true,  tension:.35},
      {label:'Forecast', data:rFcst, borderColor:'#FF6900', borderDash:[4,3], borderWidth:1.5, pointRadius:2, fill:false, tension:.35},
    ]},
    options:{ onClick: (e, elems) => { if(elems.length){ S.filterMonth = elems[0].index; onDateChange(S.date); } else { S.filterMonth=null; onDateChange(S.date); } }, responsive:true, maintainAspectRatio:false, plugins:{legend:baseLegend, tooltip:{cornerRadius:6, callbacks:{label:ctx=>` ${ctx.dataset.label}: ${eur(ctx.parsed.y)}`}}}, scales:baseScales },
  });

  // 2. Expenditure doughnut
  const expCats = categories.filter(c=>c.type==='expenditure');
  const dColors = ['#0F172A','#1E293B','#009A3D','#FF6900','#E91E8C','#0097A7','#8D6E63'];
  S.charts.exp = new Chart(el('chart-expense'), {
    type:'doughnut',
    data:{ labels:expCats.map(c=>c.label), datasets:[{
      data: expCats.map(c=>S.filterMonth !== null ? (c.actual[S.filterMonth]||0) : c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0)),
      backgroundColor:dColors, borderWidth:2, borderColor:'#fff',
    }]},
    options:{ responsive:true, maintainAspectRatio:false, plugins:{
      legend:{ position:'right', labels:{font:CF, padding:10} },
      tooltip:{ callbacks:{label:ctx=>` ${ctx.label}: ${eur(ctx.parsed)}`} },
    }},
  });

  // 3. Surplus trend line
  const surpAct  = months.map((_,i)=>{
    if(i>=AM) return null;
    const r=categories.filter(c=>c.type==='revenue').reduce((s,c)=>s+(c.actual[i]||0),0);
    const e=categories.filter(c=>c.type==='expenditure').reduce((s,c)=>s+(c.actual[i]||0),0);
    return r-e;
  });
  const surpFcst = months.map((_,i)=>{
    if(i<max_months) return null;
    const r=categories.filter(c=>c.type==='revenue').reduce((s,c)=>s+(c.forecast[i]||c.budget[i]||0),0);
    const e=categories.filter(c=>c.type==='expenditure').reduce((s,c)=>s+(c.forecast[i]||c.budget[i]||0),0);
    return r-e;
  });
  const surpBudg = months.map((_,i)=>{
    const r=categories.filter(c=>c.type==='revenue').reduce((s,c)=>s+c.budget[i],0);
    const e=categories.filter(c=>c.type==='expenditure').reduce((s,c)=>s+c.budget[i],0);
    return r-e;
  });

  S.charts.surp = new Chart(el('chart-surplus'), {
    type:'line',
    data:{ labels:months, datasets:[
      {label:'Budget',   data:surpBudg, borderColor:'#334155', borderDash:[4,3], borderWidth:1.5, pointRadius:2, fill:false, tension:.35},
      {label:'Actual',   data:surpAct,  borderColor:'#0F172A', backgroundColor:'rgba(15,23,42,.1)', borderWidth:2, pointRadius:3, fill:true, tension:.35},
      {label:'Forecast', data:surpFcst, borderColor:'#FF6900', borderDash:[4,3], borderWidth:1.5, pointRadius:2, fill:false, tension:.35},
    ]},
    options:{ onClick: (e, elems) => { if(elems.length){ S.filterMonth = elems[0].index; onDateChange(S.date); } else { S.filterMonth=null; onDateChange(S.date); } }, responsive:true, maintainAspectRatio:false, plugins:{legend:baseLegend, tooltip:{cornerRadius:6, callbacks:{label:ctx=>` ${ctx.dataset.label}: ${eur(ctx.parsed.y)}`}}}, scales:baseScales },
  });

  // 4. Variance bar (horizontal)
  const varItems = categories.map(c=>{
    const b = S.filterMonth !== null ? (c.budget[S.filterMonth]||0) : c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const a = S.filterMonth !== null ? (c.actual[S.filterMonth]||0) : c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);
    return { label:c.label, type:c.type, v:a-b };
  }).filter(x=>Math.abs(x.v)>200).sort((a,b)=>Math.abs(b.v)-Math.abs(a.v)).slice(0,8);

  S.charts.var = new Chart(el('chart-variance'), {
    type:'bar',
    data:{ labels:varItems.map(d=>d.label), datasets:[{
      label:'Variance €',
      data:varItems.map(d=>d.v),
      backgroundColor:varItems.map(d=>{
        const fav=d.type==='revenue'?d.v>0:d.v<0;
        return fav?'rgba(0,154,61,.7)':'rgba(192,57,43,.7)';
      }),
      borderRadius:3, borderWidth:0,
    }]},
    options:{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
      plugins:{ legend:{display:false}, tooltip:{cornerRadius:6, callbacks:{label:ctx=>` ${eur(ctx.parsed.x)}`}} },
      scales:{
        x:{ grid:{color:'rgba(0,0,0,.04)'}, ticks:{font:CF, callback:v=>'€'+Math.round(v/1000)+'k'} },
        y:{ grid:{display:false}, ticks:{font:{...CF,size:10}} },
      },
    },
  });

  
  // Update point styles to highlight selected month
  if (S.filterMonth !== null) {
    [S.charts.rev, S.charts.surp].forEach(ch => {
      ch.data.datasets.forEach(ds => {
        ds.radius = ctx => ctx.dataIndex === S.filterMonth ? 6 : 2;
        ds.borderWidth = ctx => ctx.dataIndex === S.filterMonth ? 4 : 2;
      });
      ch.update();
    });
  }

  // School summary table
  el('dash-schools-tbody').innerHTML = schools.map(s => {
    const rb = S.filterMonth !== null && s.rev_b_months ? s.rev_b_months[S.filterMonth] : s.ytd_revenue_budget;
    const ra = S.filterMonth !== null && s.rev_a_months ? s.rev_a_months[S.filterMonth] : s.ytd_revenue_actual;
    const eb = S.filterMonth !== null && s.exp_b_months ? s.exp_b_months[S.filterMonth] : s.ytd_expenditure_budget;
    const ea = S.filterMonth !== null && s.exp_a_months ? s.exp_a_months[S.filterMonth] : s.ytd_expenditure_actual;
    const sA = ra - ea;
    const sB = rb - eb;
    const surpV = sA - sB;
    const surpP = sB ? surpV/Math.abs(sB)*100 : 0;
    return `<tr style="cursor:pointer" onclick="document.getElementById('school-select').value='${s.id}'; onSchoolChange('${s.id}')">
      <td><strong>${s.name}</strong></td>
      <td style="color:var(--muted)">${s.segment}</td>
      <td class="num">${s.headcount.toLocaleString()}</td>
      <td class="num">${eur(ra)}</td>
      <td class="num">${eur(ea)}</td>
      <td class="num ${sA>=0?'fav':'adv'}">${eur(sA)}</td>
      <td class="num ${varCls(surpP,'revenue')}">${fmt_pct(surpP)}</td>
    </tr>`;
  }).join('');

  hide('dash-loading');
  const dc = el('dash-content');
  if (dc) dc.style.display = 'flex';
}

// ════════════════════════════════════════════════
// DATA INPUT
// ════════════════════════════════════════════════
function renderInput() {
  // Schools table
  el('input-schools-tbody').innerHTML = S.inputSchools.map((s, i) => `
    <tr>
      <td><strong>${s.name}</strong></td>
      <td style="color:var(--muted)">${s.segment}</td>
      <td class="num">
        <input type="number" class="input-cell" value="${s.headcount}" min="10" max="3000"
          onchange="S.inputSchools[${i}].headcount=+this.value; updateRevRow(${i})">
      </td>
      <td class="num">
        <input type="number" class="input-cell" value="${s.revenue_per_head}" min="1000" max="12000" step="100"
          onchange="S.inputSchools[${i}].revenue_per_head=+this.value; updateRevRow(${i})">
      </td>
      <td class="num" id="rev-row-${i}">${eur(s.headcount * s.revenue_per_head)}</td>
    </tr>`).join('');

  // Ratios
  el('ratios-grid').innerHTML = Object.entries(DEF_RATIOS).map(([key]) => `
    <div class="ratio-card">
      <span class="ratio-label">${RATIO_LABELS[key]}</span>
      <div class="ratio-input-wrap">
        <input type="range" class="ratio-slider" id="slider-${key}"
          value="${(S.inputRatios[key]*100).toFixed(1)}" min="1" max="60" step="0.5"
          oninput="S.inputRatios['${key}']=+this.value/100; el('ratio-val-${key}').textContent=parseFloat(this.value).toFixed(1)+'%'">
        <span class="ratio-value" id="ratio-val-${key}">${(S.inputRatios[key]*100).toFixed(1)}%</span>
      </div>
    </div>`).join('');
}

function updateRevRow(i) {
  const s = S.inputSchools[i];
  const e = el(`rev-row-${i}`);
  if (e) e.textContent = eur(s.headcount * s.revenue_per_head);
}

async function applyAssumptions() {
  const btn = el('btn-apply');
  const status = el('apply-status');
  btn.disabled = true; btn.textContent = '⏳ Recalculating…';
  status.textContent = '';
  try {
    const fpna = await api('/api/recalculate', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ schools: S.inputSchools, ratios: S.inputRatios }),
    });
    // Invalidate caches and reload dashboard
    S.dashCache = {}; S.fpnaCache = {}; S.varCache = {};
    S.dashCache[S.school] = null;
    status.textContent = '✓ Updated';
    status.style.color = 'var(--green)';
    switchTab('dashboard');
  } catch(e) {
    status.textContent = '⚠ ' + e.message;
    status.style.color = 'var(--red)';
  } finally {
    btn.disabled = false; btn.textContent = 'Apply & Recalculate';
  }
}

function resetAssumptions() {
  S.inputSchools = DEF_REGIONS.map(s => ({...s}));
  S.inputRatios  = {...DEF_RATIOS};
  S.dashCache = {}; S.fpnaCache = {}; S.varCache = {};
  renderInput();
  el('apply-status').textContent = '';
}

// ════════════════════════════════════════════════
// FP&A ENGINE
// ════════════════════════════════════════════════
async function loadFpna(sid) {
  show('fpna-loading'); hide('fpna-content');
  try {
    const d = await api(`/api/fpna/${sid}?city=${S.city}&version=${S.version}`);
    S.fpnaCache[sid] = d;
    renderFpna(d);
  } catch(e) { el('fpna-loading').textContent = '⚠ ' + e.message; }
}

function renderFpna(data) {
  let { school, months, actual_months:AM, categories } = data;
  let max_months = (S.date === 'ytd' && AM > 0) ? AM : months.length;
  let revB=0,revA=0,expB=0,expA=0;
  categories.forEach(c=>{
    const bS=c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const aS=c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);
    if(c.type==='revenue'){revB+=bS;revA+=aS;}else{expB+=bS;expA+=aS;}
  });
  const surpA=revA-expA, surpB=revB-expB;

  el('fpna-kpis').innerHTML = `
    <div class="kpi-card ${revA>=revB?'green':'amber'}">
      <div class="kpi-label">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Revenue</div><div class="kpi-value">${shortEur(revA)}</div>
      <div class="kpi-sub">Budget: ${shortEur(revB)}</div>${delta(revA,revB,'revenue')}${chip(insight(revA,revB,'revenue'))}
    </div>
    <div class="kpi-card ${expA<=expB?'green':'amber'}">
      <div class="kpi-label">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Expenditure</div><div class="kpi-value">${shortEur(expA)}</div>
      <div class="kpi-sub">Budget: ${shortEur(expB)}</div>${delta(expA,expB,'expenditure')}${chip(insight(expA,expB,'expenditure'))}
    </div>
    <div class="kpi-card ${surpA>=surpB?'green':'red'}">
      <div class="kpi-label">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Surplus</div><div class="kpi-value">${shortEur(surpA)}</div>
      <div class="kpi-sub">Budget: ${shortEur(surpB)}</div>${delta(surpA,surpB,'revenue')}${chip(surInsight(surpA,surpB))}
    </div>
    <div class="kpi-card amber">
      <div class="kpi-label">Entity</div>
      <div class="kpi-value" style="font-size:15px">${school.name.split(' ').slice(0,2).join(' ')}</div>
      <div class="kpi-sub">${school.headcount.toLocaleString()} headcount</div>
      ${chip({text:`${AM} months actuals · ${12-AM} months forecast`})}
    </div>`;

  el('fpna-thead').innerHTML = `<tr>
    <th style="min-width:180px">Category</th>
    ${months.map((m,i)=>`<th class="num" style="${AM>0 && i>=AM?'opacity:.7':''}">${m}${AM>0 && i>=AM?' ᶠ':''}</th>`).join('')}
    <th class="num">Budget</th><th class="num">Actual</th>
    <th class="num">Variance €</th><th class="num">Var %</th>
  </tr>`;

  let rows = '';
  ['revenue','expenditure'].forEach(sec => {
    const cats = categories.filter(c=>c.type===sec);
    rows += `<tr class="row-sec"><td colspan="${months.length+5}">${sec.toUpperCase()}</td></tr>`;
    let secB=0,secA=0;
    cats.forEach(c=>{
      const ytdB=c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
      const ytdA=c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);
      const v=ytdA-ytdB, p=ytdB?v/ytdB*100:0;
      secB+=ytdB; secA+=ytdA;
      const cells=months.map((_,i)=>{
        if(c.actual[i]!=null) return `<td class="num cell-a">${eur(c.actual[i])}</td>`;
        if(c.forecast[i]!=null) return `<td class="num cell-f">${eur(c.forecast[i])}</td>`;
        return `<td class="num cell-b" style="opacity:.6">${eur(c.budget[i])}</td>`;
      }).join('');
      rows += `<tr>
        <td style="padding-left:22px;color:var(--muted)">${c.label}</td>${cells}
        <td class="num cell-b">${eur(ytdB)}</td><td class="num cell-a">${eur(ytdA)}</td>
        <td class="num ${varCls(v,c.type)}">${eur(v)}</td><td class="num ${varCls(p,c.type)}">${fmt_pct(p)}</td>
      </tr>`;
    });
    const tv=secA-secB, tp=secB?tv/secB*100:0;
    rows += `<tr class="row-total">
      <td><strong>Total ${sec.toUpperCase()}</strong></td>${months.map(()=>'<td></td>').join('')}
      <td class="num">${eur(secB)}</td><td class="num"><strong>${eur(secA)}</strong></td>
      <td class="num ${varCls(tv,sec)}">${eur(tv)}</td><td class="num ${varCls(tp,sec)}">${fmt_pct(tp)}</td>
    </tr>`;
  });
  const sv=surpA-surpB, sp=surpB?sv/Math.abs(surpB)*100:0;
  rows += `<tr class="row-net">
    <td><strong>NET SURPLUS / (DEFICIT)</strong></td>${months.map(()=>'<td></td>').join('')}
    <td class="num">${eur(surpB)}</td><td class="num">${eur(surpA)}</td>
    <td class="num ${sv>=0?'fav':'adv'}">${eur(sv)}</td><td class="num ${sv>=0?'fav':'adv'}">${fmt_pct(sp)}</td>
  </tr>`;
  el('fpna-tbody').innerHTML = rows;
  hide('fpna-loading'); show('fpna-content');
}

// ════════════════════════════════════════════════
// AI INSIGHTS
// ════════════════════════════════════════════════
async function loadAi(sid) {
  show('ai-loading'); hide('ai-content');
  el('ai-panel-body').innerHTML = `<div class="ai-placeholder"><div style="font-size:28px;margin-bottom:10px;opacity:.3">✦</div><div style="font-weight:600;margin-bottom:6px;color:var(--muted)">Ready to analyse</div><div style="font-size:12.5px;color:var(--muted)">Click "Explain with AI" to generate a detailed narrative, or "Board Commentary" for a formal report.</div></div>`;
  el('risk-badge').textContent = '';
  try {
    const d = await api(`/api/variance/${sid}?city=${S.city}&version=${S.version}`);
    S.varCache[sid] = d;
    renderVariance(d);
  } catch(e) { el('ai-loading').textContent = '⚠ ' + e.message; }
}

function renderVariance(d) {
  el('ai-entity-label').textContent = d.school.name;
  el('variance-tbody').innerHTML = d.significant_variances.length
    ? d.significant_variances.map(v => {
        const fav = v.type==='revenue' ? v.pct_variance>0 : v.pct_variance<0;
        const abs = Math.abs(v.pct_variance);
        const flag = fav ? `<span class="ai-flag low">✓ Favourable</span>`
                    : abs>=8 ? `<span class="ai-flag high">⚠ High</span>`
                    : abs>=4 ? `<span class="ai-flag medium">△ Monitor</span>`
                    : `<span class="ai-flag low">✓ Low</span>`;
        return `<tr>
          <td><strong>${v.category}</strong></td>
          <td style="color:var(--muted);font-size:12px">${v.type}</td>
          <td class="num">${eur(v.budget_ytd)}</td>
          <td class="num">${eur(v.actual_ytd)}</td>
          <td class="num ${varCls(v.variance,v.type)}">${eur(v.variance)}</td>
          <td class="num ${varCls(v.pct_variance,v.type)}">${fmt_pct(v.pct_variance)}</td>
          <td>${flag}</td>
        </tr>`;
      }).join('')
    : '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">No significant variances</td></tr>';
  hide('ai-loading'); show('ai-content');
}

async function explainVariance() {
  const btn = el('btn-explain');
  btn.disabled = true; btn.textContent = '⏳ Analysing…';
  el('ai-panel-body').innerHTML = '<div class="ai-spinner">Gemini is analysing…</div>';
  el('risk-badge').textContent = '';
  try {
    const d = S.varCache[S.school];
    const res = await api('/api/ai/explain-variance', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ school_name:d.school.name, variances:d.significant_variances }),
    });
    el('ai-panel-body').innerHTML = `<div class="ai-text">${res.explanation}</div>`;
    el('risk-badge').textContent = 'Risk: ' + res.risk_rating;
    el('risk-badge').className = 'risk-badge ' + (res.risk_rating||'').toLowerCase();
  } catch(e) {
    el('ai-panel-body').innerHTML = `<p style="color:var(--red)">⚠ ${e.message}</p>`;
  } finally {
    btn.disabled = false; btn.textContent = '✦ Explain with AI';
  }
}

async function generateBoardCommentary() {
  const btn = el('btn-board');
  btn.disabled = true; btn.textContent = '⏳ Generating…';
  el('ai-panel-body').innerHTML = '<div class="ai-spinner">Generating board commentary…</div>';
  el('risk-badge').textContent = '';
  const d = S.varCache[S.school];
  const rev = d.significant_variances.filter(v=>v.type==='revenue');
  const exp = d.significant_variances.filter(v=>v.type==='expenditure');
  const summary = {
    revenue_budget: rev.reduce((s,v)=>s+v.budget_ytd,0),
    revenue_actual: rev.reduce((s,v)=>s+v.actual_ytd,0),
    exp_budget:     exp.reduce((s,v)=>s+v.budget_ytd,0),
    exp_actual:     exp.reduce((s,v)=>s+v.actual_ytd,0),
  };
  summary.surplus_budget = summary.revenue_budget - summary.exp_budget;
  summary.surplus_actual = summary.revenue_actual - summary.exp_actual;
  try {
    const res = await api('/api/ai/board-commentary', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ school_name:d.school.name, summary }),
    });
    el('ai-panel-body').innerHTML = `<div class="ai-text">${res.commentary}</div>`;
  } catch(e) {
    el('ai-panel-body').innerHTML = `<p style="color:var(--red)">⚠ ${e.message}</p>`;
  } finally {
    btn.disabled = false; btn.textContent = '📄 Board Commentary';
  }
}

// ── Utils ─────────────────────────────────────────
const el = id => document.getElementById(id);
const show = id => { const e=el(id); if(e) e.style.display='block'; };
const hide = id => { const e=el(id); if(e) e.style.display='none'; };

// ── Init ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => switchTab('dashboard'));
