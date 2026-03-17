import os
import re

DIR = r"c:\Users\r.hadjicharalambous\OneDrive - Grant Thornton Cyprus\Desktop\PascalExample"

def process_file(path, func):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = func(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def update_js(text):
    # 1. State changes
    text = text.replace("date:      'ytd',", "date:      'ytd',\n  filterMonth: null,")
    
    # 2. Add chart click handler logic
    chart_click_handler = """
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
}"""
    text = text.replace("function onRegionChange(v) {", chart_click_handler + "\nfunction onRegionChange(v) {")
    text = text.replace("function onSchoolChange(v) {", chart_click_handler + "\nfunction onSchoolChange(v) {")

    # 3. Modify renderDashboard aggregations to respect filterMonth
    # Total calculations
    agg_old = """  let revB=0, revA=0, expB=0, expA=0;
  categories.forEach(c => {
    const bS = c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const aS = c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);
    if (c.type==='revenue') { revB+=bS; revA+=aS; }
    else                    { expB+=bS; expA+=aS; }
  });"""
    
    agg_new = """  let revB=0, revA=0, expB=0, expA=0;
  categories.forEach(c => {
    const bS = S.filterMonth !== null ? (c.budget[S.filterMonth]||0) : c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const aS = S.filterMonth !== null ? (c.actual[S.filterMonth]||0) : c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);
    if (c.type==='revenue') { revB+=bS; revA+=aS; }
    else                    { expB+=bS; expA+=aS; }
  });"""
    text = text.replace(agg_old, agg_new)
    
    # Update KPI Month name if filter is active
    kpi_old = "      <div class=\"kpi-label\">YTD Revenue</div>"
    kpi_new = "      <div class=\"kpi-label\">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Revenue</div>"
    text = text.replace(kpi_old, kpi_new)
    text = text.replace("<div class=\"kpi-label\">YTD Expenditure</div>", "<div class=\"kpi-label\">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Expenditure</div>")
    text = text.replace("<div class=\"kpi-label\">YTD Surplus</div>", "<div class=\"kpi-label\">${S.filterMonth !== null ? months[S.filterMonth] : 'YTD'} Surplus</div>")

    # Chart onClick bindings inside renderDashboard
    # Doughnut chart aggregation
    doughnut_old = "      data: expCats.map(c=>c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0)),"
    doughnut_new = "      data: expCats.map(c=>S.filterMonth !== null ? (c.actual[S.filterMonth]||0) : c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0)),"
    text = text.replace(doughnut_old, doughnut_new)

    # Variance bar chart aggregation
    var_old = """    const b=c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const a=c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);"""
    var_new = """    const b = S.filterMonth !== null ? (c.budget[S.filterMonth]||0) : c.budget.slice(0,max_months).reduce((s,x)=>s+x,0);
    const a = S.filterMonth !== null ? (c.actual[S.filterMonth]||0) : c.actual.slice(0,max_months).reduce((s,x)=>s+(x||0),0);"""
    text = text.replace(var_old, var_new)

    # Inject onClick to charts
    chart_opts_rev = "options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:baseLegend, tooltip:{cornerRadius:6, callbacks:{label:ctx=>` ${ctx.dataset.label}: ${eur(ctx.parsed.y)}`}}}, scales:baseScales },"
    chart_opts_rev_new = "options:{ onClick: (e, elems) => { if(elems.length){ S.filterMonth = elems[0].index; onDateChange(S.date); } else { S.filterMonth=null; onDateChange(S.date); } }, responsive:true, maintainAspectRatio:false, plugins:{legend:baseLegend, tooltip:{cornerRadius:6, callbacks:{label:ctx=>` ${ctx.dataset.label}: ${eur(ctx.parsed.y)}`}}}, scales:baseScales },"
    text = text.replace(chart_opts_rev, chart_opts_rev_new)

    # Make table rows clickable
    tbl_old = "    return `<tr>"
    tbl_new = "    const rb = S.filterMonth !== null && s.rev_b_months ? s.rev_b_months[S.filterMonth] : s.ytd_revenue_budget;\n    const ra = S.filterMonth !== null && s.rev_a_months ? s.rev_a_months[S.filterMonth] : s.ytd_revenue_actual;\n    const eb = S.filterMonth !== null && s.exp_b_months ? s.exp_b_months[S.filterMonth] : s.ytd_expenditure_budget;\n    const ea = S.filterMonth !== null && s.exp_a_months ? s.exp_a_months[S.filterMonth] : s.ytd_expenditure_actual;\n    const surpA = ra - ea;\n    const surpB = rb - eb;\n    const surpP = surpB ? surpV/Math.abs(surpB)*100 : 0;\n    return `<tr style=\"cursor:pointer\" onclick=\"document.getElementById('school-select').value='${s.id}'; onSchoolChange('${s.id}')\">"
    text = text.replace(tbl_old, tbl_new)
    text = text.replace("const surpP = s.ytd_surplus_budget ? surpV/Math.abs(s.ytd_surplus_budget)*100 : 0;", "")
    text = text.replace("const surpV = s.ytd_surplus_actual - s.ytd_surplus_budget;", "const surpV = surpA - surpB;")
    text = text.replace("${eur(s.ytd_revenue_actual)}", "${eur(ra)}")
    text = text.replace("${eur(s.ytd_expenditure_actual)}", "${eur(ea)}")
    text = text.replace("${eur(s.ytd_surplus_actual)}", "${eur(surpA)}")
    text = text.replace("${s.ytd_surplus_actual>=0", "${surpA>=0")
    
    # Highlight specific month in chart when selected
    hilite_code = """
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
"""
    # put the hilite code right before schools render
    text = text.replace("// School summary table", hilite_code + "\n  // School summary table")

    return text

process_file(os.path.join(DIR, "public", "js", "app.js"), update_js)
print("Interactive updates applied!")
