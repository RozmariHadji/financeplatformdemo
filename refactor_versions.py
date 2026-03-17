import os
import re

DIR = r"c:\Users\r.hadjicharalambous\OneDrive - Grant Thornton Cyprus\Desktop\PascalExample"

def process_file(path, func):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = func(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def update_python(text):
    # Let's replace generate_school_data and the API endpoints to use versions.
    
    # 1. Update generate_school_data
    gen_old = """def generate_school_data(school: dict, seed: int) -> dict:
    rng = random.Random(seed)
    result = {}
    for cat in CATEGORIES:
        key = cat["key"]
        typ = cat["type"]
        annual = annual_budget(school["headcount"], key)
        seas = SEASONALITY_REV if typ == "revenue" else SEASONALITY_EXP
        total_w = sum(seas)

        budget, actual, forecast = [], [], []
        for i in range(12):
            b = round(annual / total_w * seas[i])
            budget.append(b)
            if i < ACTUAL_MONTHS:
                factor = rng.gauss(1.0, 0.04)
                if rng.random() < 0.20:
                    factor = rng.gauss(1.10, 0.03)
                actual.append(round(b * factor))
                forecast.append(None)
            else:
                actual.append(None)
                forecast.append(round(b * rng.gauss(1.02, 0.015)))
        result[key] = {"budget": budget, "actual": actual, "forecast": forecast}
    return result"""

    gen_new = """def generate_school_data(school: dict, seed: int) -> dict:
    rng = random.Random(seed)
    result = {}
    for cat in CATEGORIES:
        key = cat["key"]
        typ = cat["type"]
        annual = annual_budget(school["headcount"], key)
        seas = SEASONALITY_REV if typ == "revenue" else SEASONALITY_EXP
        total_w = sum(seas)

        base_budget = []
        full_actual = []
        full_forecast = []
        for i in range(12):
            b = round(annual / total_w * seas[i])
            base_budget.append(b)
            factor = rng.gauss(1.0, 0.04)
            if rng.random() < 0.20: factor = rng.gauss(1.10, 0.03)
            full_actual.append(round(b * factor))
            full_forecast.append(round(b * rng.gauss(1.02, 0.015)))
        
        # 5 year data
        five_year = []
        base_yr = sum(base_budget)
        for y in range(5):
            five_year.append(round(base_yr * (1.05 ** y))) # 5% growth

        result[key] = {
            "base_budget": base_budget,
            "full_actual": full_actual,
            "full_forecast": full_forecast,
            "five_year": five_year
        }
    return result

def get_versioned_data(d, version):
    b = d["base_budget"][:]
    a = [None]*12
    f = [None]*12
    m = MONTHS[:]
    am = ACTUAL_MONTHS
    
    if version == "ongoing_rolling":
        a = d["full_actual"][:9] + [None]*3
        f = [None]*9 + d["full_forecast"][9:]
        am = 9
    elif version == "initial_budget":
        a = [None]*12
        f = [None]*12
        am = 0
    elif version == "irb":
        a = d["full_actual"][:9] + [None]*3
        f = [None]*9 + d["base_budget"][9:]
        am = 9
    elif version == "final":
        a = d["full_actual"][:]
        f = [None]*12
        am = 12
    elif version == "forecast_5_7":
        a = d["full_actual"][:5] + [None]*7
        f = [None]*5 + d["full_forecast"][5:]
        am = 5
    elif version == "forecast_8_4":
        a = d["full_actual"][:8] + [None]*4
        f = [None]*8 + d["full_forecast"][8:]
        am = 8
    elif version == "5_year":
        b = d["five_year"][:]
        a = [None]*5
        f = [None]*5
        m = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
        am = 0

    return {"budget": b, "actual": a, "forecast": f, "months": m, "actual_months": am}
"""
    text = text.replace(gen_old, gen_new)

    # 2. Update build_fpna
    build_old = """def build_fpna(school: dict, sdata: dict) -> dict:
    cats = []
    for cat in CATEGORIES:
        key = cat["key"]
        d = sdata[key]
        v, p = variance(d["budget"], d["actual"])
        cats.append({
            "key": key,
            "label": cat["label"],
            "type": cat["type"],
            "budget": d["budget"],
            "actual": d["actual"],
            "forecast": d["forecast"],
            "variance": v,
            "pct_variance": p,
        })
    return {"school": school, "months": MONTHS, "actual_months": ACTUAL_MONTHS, "categories": cats}"""

    build_new = """def build_fpna(school: dict, sdata: dict, version="ongoing_rolling") -> dict:
    cats = []
    m = MONTHS
    am = ACTUAL_MONTHS
    for cat in CATEGORIES:
        key = cat["key"]
        vd = get_versioned_data(sdata[key], version)
        m = vd["months"]
        am = vd["actual_months"]
        v, p = variance(vd["budget"], vd["actual"])
        cats.append({
            "key": key,
            "label": cat["label"],
            "type": cat["type"],
            "budget": vd["budget"],
            "actual": vd["actual"],
            "forecast": vd["forecast"],
            "variance": v,
            "pct_variance": p,
        })
    return {"school": school, "months": m, "actual_months": am, "categories": cats, "version": version}"""
    text = text.replace(build_old, build_new)

    # 3. Update group_fpna
    grp_old = """def group_fpna(city: str = None) -> dict:
    filtered_schools = [s for s in SCHOOLS if not city or city == "all" or s["city"].lower() == city.lower()]
    merged = {}
    for cat in CATEGORIES:
        key = cat["key"]
        budget = [0] * 12
        actual = [None] * 12
        forecast = [None] * 12
        for school in filtered_schools:
            d = SCHOOL_DATA[school["id"]][key]
            for i in range(12):
                budget[i] += d["budget"][i]
                if d["actual"][i] is not None:
                    actual[i] = (actual[i] or 0) + d["actual"][i]
                if d["forecast"][i] is not None:
                    forecast[i] = (forecast[i] or 0) + d["forecast"][i]
        v, p = variance(budget, actual)"""
    
    grp_new = """def group_fpna(city: str = None, version="ongoing_rolling") -> dict:
    filtered_schools = [s for s in SCHOOLS if not city or city == "all" or s["city"].lower() == city.lower()]
    merged = {}
    m = MONTHS
    am = ACTUAL_MONTHS
    for cat in CATEGORIES:
        key = cat["key"]
        
        test_vd = get_versioned_data(SCHOOL_DATA[SCHOOLS[0]["id"]][key], version)
        m = test_vd["months"]
        am = test_vd["actual_months"]
        n_len = len(m)
        
        budget = [0] * n_len
        actual = [None] * n_len
        forecast = [None] * n_len
        
        for school in filtered_schools:
            vd = get_versioned_data(SCHOOL_DATA[school["id"]][key], version)
            for i in range(n_len):
                budget[i] += vd["budget"][i]
                if vd["actual"][i] is not None:
                    actual[i] = (actual[i] or 0) + vd["actual"][i]
                if vd["forecast"][i] is not None:
                    forecast[i] = (forecast[i] or 0) + vd["forecast"][i]
        v, p = variance(budget, actual)"""
    text = text.replace(grp_old, grp_new)

    text = text.replace('return {"school": group_school, "months": MONTHS, "actual_months": ACTUAL_MONTHS,', 'return {"school": group_school, "months": m, "actual_months": am,')

    # 4. update get_schools
    sch_old = """@app.get("/api/schools")
def get_schools(city: str = None):
    out = []
    for school in SCHOOLS:
        if city and city != "all" and school.get("city", "").lower() != city.lower():
            continue
        sid = school["id"]
        sd = SCHOOL_DATA[sid]
        rev_b = rev_a = exp_b = exp_a = 0
        rev_b_months = [0]*12
        rev_a_months = [0]*12
        exp_b_months = [0]*12
        exp_a_months = [0]*12
        for cat in CATEGORIES:
            key = cat["key"]
            for i in range(12):
                b = sd[key]["budget"][i]
                a = sd[key]["actual"][i] if sd[key]["actual"][i] is not None else 0
                if cat["type"] == "revenue":
                    rev_b_months[i] += b
                    rev_a_months[i] += a
                    if i < ACTUAL_MONTHS: rev_b += b; rev_a += a
                else:
                    exp_b_months[i] += b
                    exp_a_months[i] += a
                    if i < ACTUAL_MONTHS: exp_b += b; exp_a += a"""
                    
    sch_new = """@app.get("/api/schools")
def get_schools(city: str = None, version: str = "ongoing_rolling"):
    out = []
    
    # helper for actual months
    test_vd = get_versioned_data(SCHOOL_DATA[SCHOOLS[0]["id"]][CATEGORIES[0]["key"]], version)
    am = test_vd["actual_months"]
    n_len = len(test_vd["months"])
    
    for school in SCHOOLS:
        if city and city != "all" and school.get("city", "").lower() != city.lower():
            continue
        sid = school["id"]
        sd = SCHOOL_DATA[sid]
        rev_b = rev_a = exp_b = exp_a = 0
        rev_b_months = [0]*n_len
        rev_a_months = [0]*n_len
        exp_b_months = [0]*n_len
        exp_a_months = [0]*n_len
        for cat in CATEGORIES:
            key = cat["key"]
            vd = get_versioned_data(sd[key], version)
            for i in range(n_len):
                b = vd["budget"][i]
                a = vd["actual"][i] if vd["actual"][i] is not None else 0
                if cat["type"] == "revenue":
                    rev_b_months[i] += b
                    rev_a_months[i] += a
                    if am == 0 or i < am: rev_b += b; rev_a += a
                else:
                    exp_b_months[i] += b
                    exp_a_months[i] += a
                    if am == 0 or i < am: exp_b += b; exp_a += a"""
    text = text.replace(sch_old, sch_new)
    text = text.replace('return {"schools": out, "months": MONTHS, "actual_months": ACTUAL_MONTHS}', 'return {"schools": out, "months": test_vd["months"], "actual_months": am}')
    
    # 5. API endpoints
    text = text.replace('def get_fpna(school_id: str, city: str = None):', 'def get_fpna(school_id: str, city: str = None, version: str = "ongoing_rolling"):')
    text = text.replace('return group_fpna(city)', 'return group_fpna(city, version)')
    text = text.replace('return build_fpna(school, SCHOOL_DATA[school_id])', 'return build_fpna(school, SCHOOL_DATA[school_id], version)')

    text = text.replace('def get_variance(school_id: str, city: str = None):', 'def get_variance(school_id: str, city: str = None, version: str = "ongoing_rolling"):')
    text = text.replace('data = group_fpna(city) if school_id == "group" else get_fpna(school_id)', 'data = group_fpna(city, version) if school_id == "group" else get_fpna(school_id, city, version)')
    text = text.replace('b_ytd = sum(cat["budget"][:ACTUAL_MONTHS])', 'am = data["actual_months"]\n        b_ytd = sum(cat["budget"][:am]) if am > 0 else sum(cat["budget"])')
    text = text.replace('a_ytd = sum(x for x in cat["actual"][:ACTUAL_MONTHS] if x is not None)', 'a_ytd = sum(x for x in cat["actual"][:am] if x is not None) if am > 0 else 0')
    text = text.replace('"actual_months": ACTUAL_MONTHS,', '"actual_months": data["actual_months"],')
    text = text.replace('"months": MONTHS[:ACTUAL_MONTHS],', '"months": data["months"][:data["actual_months"]] if data["actual_months"] > 0 else data["months"],')

    return text

def update_js(text):
    # Add version to State
    text = text.replace("date:      'ytd',", "date:      'ytd',\n  version:   'ongoing_rolling',")
    
    # Add events for Version change
    events = """
function onVersionChange(v) {
  S.version = v;
  S.dashCache = {}; S.fpnaCache = {}; S.varCache = {}; // invalidate caches
  if (S.version === 'initial_budget' || S.version === '5_year') { S.date = 'full'; document.getElementById('date-select').value='full'; document.getElementById('date-select').disabled=true; } 
  else { document.getElementById('date-select').disabled=false; }
  
  if (S.tab === 'dashboard') loadDashboard(S.school);
  if (S.tab === 'fpna')      loadFpna(S.school);
  if (S.tab === 'ai')        loadAi(S.school);
}
"""
    text = text.replace("function onCityChange(v) {", events + "\nfunction onCityChange(v) {")

    # Update API calls in JS
    text = text.replace("(`${S.city}`)", "(`${S.city}&version=${S.version}`)")
    text = text.replace("api(`/api/fpna/${sid}?city=${S.city}`)", "api(`/api/fpna/${sid}?city=${S.city}&version=${S.version}`)")
    text = text.replace("api(`/api/schools?city=${S.city}`)", "api(`/api/schools?city=${S.city}&version=${S.version}`)")
    text = text.replace("api(`/api/variance/${sid}?city=${S.city}`)", "api(`/api/variance/${sid}?city=${S.city}&version=${S.version}`)")

    # Update actual months to am variable dynamically since it can be 0 or 12 or 5 depending on version
    # 'let max_months = S.date === 'ytd' ? AM : 12;' -> 'let max_months = (S.date === 'ytd' && AM > 0) ? AM : months.length;'
    text = text.replace("let max_months = S.date === 'ytd' ? AM : 12;", "let max_months = (S.date === 'ytd' && AM > 0) ? AM : months.length;")
    text = text.replace("Array(12).fill", "Array(months.length).fill")
    text = text.replace("<th class=\"num\">YTD Budget</th><th class=\"num\">YTD Actual</th>", "<th class=\"num\">Budget</th><th class=\"num\">Actual</th>")
    text = text.replace("let max_months = S.date === 'ytd' ? AM : 12;", "let max_months = (S.date === 'ytd' && AM > 0) ? AM : months.length;")
    
    # Adjust forecast slicing in dashboard charts slightly depending on am
    text = text.replace("i>=AM?", "AM>0 && i>=AM?")

    return text

def update_html(text):
    dropdown = """
          <select id="version-select" class="gt-select" onchange="onVersionChange(this.value)">
            <option value="ongoing_rolling">Ongoing Rolling Budget</option>
            <option value="initial_budget">Initial Budget</option>
            <option value="irb">Initial Rolling Budget (IRB)</option>
            <option value="final">Final Budget</option>
            <option value="forecast_5_7">5+7 Forecast</option>
            <option value="forecast_8_4">8+4 Forecast</option>
            <option value="5_year">5 Year Budget Forecast</option>
          </select>
"""
    text = text.replace('<select id="date-select"', dropdown + '          <select id="date-select"')
    return text

process_file(os.path.join(DIR, "api", "index.py"), update_python)
process_file(os.path.join(DIR, "public", "js", "app.js"), update_js)
process_file(os.path.join(DIR, "public", "index.html"), update_html)
print("Versions updated!")
