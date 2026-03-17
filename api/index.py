import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from project root (one level up from api/)
_root = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(_root, ".env"))

app = FastAPI(title="GEWiz FP&A Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Gemini setup ────────────────────────────────────────────────────────────
gemini_client = None
GEMINI_MODEL = "gemini-2.0-flash"
try:
    from google import genai as google_genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key and api_key != "your_gemini_api_key_here":
        gemini_client = google_genai.Client(api_key=api_key)
except Exception:
    pass

# ── Synthetic data ───────────────────────────────────────────────────────────
MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
ACTUAL_MONTHS = 9  # Apr–Dec 2025 have actuals; Jan–Mar 2026 are forecast

SCHOOLS = [
    {"id": "aes_nicosia", "name": "Alpha English School Nicosia", "headcount": 650, "segment": "Secondary", "city": "Nicosia"},
    {"id": "aps_nicosia", "name": "Alpha Primary School Nicosia", "headcount": 480, "segment": "Primary", "city": "Nicosia"},
    {"id": "aes_limassol", "name": "Alpha English School Limassol", "headcount": 820, "segment": "Secondary", "city": "Limassol"},
    {"id": "aes_larnaca", "name": "Alpha English School Larnaca", "headcount": 520, "segment": "Secondary", "city": "Larnaca"},
]

CATEGORIES = [
    {"key": "core_revenue",    "label": "Core Revenue",              "type": "revenue"},
    {"key": "other_income",   "label": "Other Income",             "type": "revenue"},
    {"key": "direct_labor", "label": "Direct Labor",           "type": "expenditure"},
    {"key": "indirect_labor",  "label": "Indirect Labor",            "type": "expenditure"},
    {"key": "management",     "label": "Management & Execs",  "type": "expenditure"},
    {"key": "facilities",       "label": "Facilities & Utilities",    "type": "expenditure"},
    {"key": "admin", "label": "Admin & Overhead",           "type": "expenditure"},
    {"key": "software",      "label": "Software & Tools",     "type": "expenditure"},
    {"key": "other_costs",    "label": "Other Costs",              "type": "expenditure"},
]

# Revenue and expenditure share of core_rev per category
BUDGET_RATIOS = {
    "core_revenue":    1.00,
    "other_income":   0.05,
    "direct_labor": 0.45,
    "indirect_labor":  0.15,
    "management":     0.08,
    "facilities":       0.08,
    "admin": 0.06,
    "software":      0.04,
    "other_costs":    0.03,
}

# Monthly seasonality weights (Apr to Mar)
SEASONALITY_REV = [1.0, 1.0, 0.95, 0.70, 0.70, 1.05, 1.05, 1.05, 1.05, 1.0, 1.0, 0.90]
SEASONALITY_EXP = [1.0, 1.0, 0.95, 0.60, 0.60, 1.10, 1.10, 1.10, 1.00, 1.0, 1.0, 0.95]


def annual_budget(headcount: int, key: str) -> float:
    core_rev = headcount * 4500
    return core_rev * BUDGET_RATIOS.get(key, 0)


def gen_school(school: dict, seed: int) -> dict:
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
                # introduce deliberate variance on ~20% of months
                factor = rng.gauss(1.0, 0.04)
                if rng.random() < 0.20:
                    factor = rng.gauss(1.10, 0.03)
                actual.append(round(b * factor))
                forecast.append(None)
            else:
                actual.append(None)
                forecast.append(round(b * rng.gauss(1.02, 0.015)))
    result[key] = {"budget": budget, "actual": actual, "forecast": forecast}
    return result


# Re-generate the full school correctly: loop is inside gen_school but must
# build the full dict. Rewrite cleanly:
def generate_school_data(school: dict, seed: int) -> dict:
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



SCHOOL_DATA = {s["id"]: generate_school_data(s, 42 + i * 7) for i, s in enumerate(SCHOOLS)}


def variance(budget: list, actual: list):
    var, pct = [], []
    for b, a in zip(budget, actual):
        if a is not None:
            v = a - b
            var.append(round(v))
            pct.append(round(v / b * 100, 1) if b else 0)
        else:
            var.append(None)
            pct.append(None)
    return var, pct


def build_fpna(school: dict, sdata: dict, version="ongoing_rolling") -> dict:
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
    return {"school": school, "months": m, "actual_months": am, "categories": cats, "version": version}


def group_fpna(city: str = None, version="ongoing_rolling") -> dict:
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
        v, p = variance(budget, actual)
        merged[key] = {
            "key": key, "label": cat["label"], "type": cat["type"],
            "budget": [round(x) for x in budget],
            "actual": [round(x) if x is not None else None for x in actual],
            "forecast": [round(x) if x is not None else None for x in forecast],
            "variance": v, "pct_variance": p,
        }
    group_school = {
        "id": "group",
        "name": "Alpha Education Group (Consolidated)",
        "headcount": sum(s["headcount"] for s in filtered_schools),
        "segment": "Multi-segment",
    }
    return {"school": group_school, "months": m, "actual_months": am,
            "categories": list(merged.values())}


# ── API routes ────────────────────────────────────────────────────────────────
@app.get("/api/schools")
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
                    if am == 0 or i < am: exp_b += b; exp_a += a
        out.append({**school,
                    "ytd_revenue_budget": round(rev_b),
                    "ytd_revenue_actual": round(rev_a),
                    "ytd_expenditure_budget": round(exp_b),
                    "ytd_expenditure_actual": round(exp_a),
                    "ytd_surplus_budget": round(rev_b - exp_b),
                    "ytd_surplus_actual": round(rev_a - exp_a),
                    "rev_b_months": rev_b_months,
                    "rev_a_months": rev_a_months,
                    "exp_b_months": exp_b_months,
                    "exp_a_months": exp_a_months,
                    "erp_status": "Connected", "erp_system": "SIMS"})
    return {"schools": out, "months": test_vd["months"], "actual_months": am}


@app.get("/api/fpna/{school_id}")
def get_fpna(school_id: str, city: str = None, version: str = "ongoing_rolling"):
    if school_id == "group":
        return group_fpna(city, version)
    school = next((s for s in SCHOOLS if s["id"] == school_id), None)
    if not school:
        raise HTTPException(404, "School not found")
    return build_fpna(school, SCHOOL_DATA[school_id], version)


@app.get("/api/variance/{school_id}")
def get_variance(school_id: str, city: str = None, version: str = "ongoing_rolling"):
    data = group_fpna(city, version) if school_id == "group" else get_fpna(school_id, city, version)
    significant = []
    for cat in data["categories"]:
        am = data["actual_months"]
        b_ytd = sum(cat["budget"][:am]) if am > 0 else sum(cat["budget"])
        a_ytd = sum(x for x in cat["actual"][:am] if x is not None) if am > 0 else 0
        var = a_ytd - b_ytd
        pct = round(var / b_ytd * 100, 1) if b_ytd else 0
        if abs(pct) > 2:
            significant.append({
                "category": cat["label"], "type": cat["type"],
                "budget_ytd": round(b_ytd), "actual_ytd": round(a_ytd),
                "variance": round(var), "pct_variance": pct,
            })
    return {
        "school": data["school"],
        "significant_variances": sorted(significant, key=lambda x: abs(x["pct_variance"]), reverse=True),
        "actual_months": data["actual_months"],
        "months": data["months"][:data["actual_months"]] if data["actual_months"] > 0 else data["months"],
    }


@app.get("/api/consolidation")
def get_consolidation():
    rows = []
    for s in SCHOOLS:
        rev = sum(annual_budget(s["headcount"], c["key"]) for c in CATEGORIES if c["type"] == "revenue")
        exp = sum(annual_budget(s["headcount"], c["key"]) for c in CATEGORIES if c["type"] == "expenditure")
        rows.append({"school": s["name"], "headcount": s["headcount"],
                     "annual_revenue": round(rev), "annual_expenditure": round(exp),
                     "annual_surplus": round(rev - exp)})
    return {"schools": rows,
            "group": {"annual_revenue": sum(r["annual_revenue"] for r in rows),
                      "annual_expenditure": sum(r["annual_expenditure"] for r in rows),
                      "annual_surplus": sum(r["annual_surplus"] for r in rows)}}


# ── AI endpoints ──────────────────────────────────────────────────────────────
class VarianceRequest(BaseModel):
    school_name: str
    variances: list


class CommentaryRequest(BaseModel):
    school_name: str
    summary: dict


@app.post("/api/ai/explain-variance")
def explain_variance(req: VarianceRequest):
    if not gemini_client:
        return {"explanation": "⚠️ AI service not configured. Add your GEMINI_API_KEY to the .env file.",
                "key_drivers": [], "risk_rating": "N/A"}
    lines = "\n".join(
        f"• {v['category']} ({v['type']}): Budget €{v['budget_ytd']:,} | "
        f"Actual €{v['actual_ytd']:,} | Variance €{v['variance']:,} ({v['pct_variance']}%)"
        for v in req.variances
    )
    prompt = f"""You are a senior financial analyst at Grant Thornton advising on school budget performance.

School: {req.school_name}
Period: April–December 2025 (Year to Date)

Significant budget variances identified:
{lines}

Write a concise financial commentary (3–4 paragraphs) for a Finance Director covering:
1. Overall YTD financial performance
2. Key drivers behind the significant variances
3. Risk areas and concerns
4. Recommended management actions

Tone: professional, direct, suitable for a Finance Director. Plain paragraphs only."""
    try:
        resp = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        max_pct = max((abs(v["pct_variance"]) for v in req.variances), default=0)
        risk = "High" if max_pct > 10 else "Medium" if max_pct > 5 else "Low"
        return {"explanation": resp.text,
                "key_drivers": [v["category"] for v in req.variances[:3]],
                "risk_rating": risk}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/ai/board-commentary")
def board_commentary(req: CommentaryRequest):
    if not gemini_client:
        return {"commentary": "⚠️ AI service not configured. Add your GEMINI_API_KEY to the .env file."}
    s = req.summary
    prompt = f"""You are a Finance Director at an Academy Trust preparing a formal board report.

Organisation: {req.school_name}
Period: April–December 2025 (Year to Date)

Financial Summary:
- Total Revenue:      €{s.get('revenue_actual', 0):,} (Budget: €{s.get('revenue_budget', 0):,})
- Total Expenditure:  €{s.get('exp_actual', 0):,}     (Budget: €{s.get('exp_budget', 0):,})
- Surplus/(Deficit):  €{s.get('surplus_actual', 0):,}  (Budget: €{s.get('surplus_budget', 0):,})

Write a formal Board Management Commentary for the Trustees covering:
## Financial Highlights
(3 bullet points)

## Key Variances
(explanation of main variances)

## Year-end Forecast
(outlook to March 2026)

## Governance & Risk
(any material risks or actions required)

Formal language appropriate for a Board of Trustees."""
    try:
        resp = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return {"commentary": resp.text}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Recalculate with custom assumptions ──────────────────────────────────────
class SchoolInput(BaseModel):
    id: str
    name: str
    headcount: int
    segment: str
    revenue_per_head: float = 4500


class RecalcRequest(BaseModel):
    schools: list
    ratios: dict


def generate_custom_data(school: dict, seed: int, ratios: dict, revenue_per_head: float) -> dict:
    rng = random.Random(seed)
    result = {}
    core_rev = school["headcount"] * revenue_per_head
    for cat in CATEGORIES:
        key = cat["key"]
        typ = cat["type"]
        if key == "core_revenue":
            annual = core_rev
        elif key == "other_income":
            annual = core_rev * 0.05
        else:
            annual = core_rev * ratios.get(key, BUDGET_RATIOS.get(key, 0))
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
    return result


@app.post("/api/recalculate")
def recalculate(req: RecalcRequest):
    custom_schools = req.schools
    custom_ratios = req.ratios or BUDGET_RATIOS
    custom_data = {
        s["id"]: generate_custom_data(s, 42 + i * 7, custom_ratios, s.get("revenue_per_head", 4500))
        for i, s in enumerate(custom_schools)
    }
    merged = {}
    for cat in CATEGORIES:
        key = cat["key"]
        budget = [0] * 12
        actual = [None] * 12
        forecast = [None] * 12
        for school in custom_schools:
            d = custom_data[school["id"]][key]
            for i in range(12):
                budget[i] += d["budget"][i]
                if d["actual"][i] is not None:
                    actual[i] = (actual[i] or 0) + d["actual"][i]
                if d["forecast"][i] is not None:
                    forecast[i] = (forecast[i] or 0) + d["forecast"][i]
        v, p = variance(budget, actual)
        merged[key] = {
            "key": key, "label": cat["label"], "type": cat["type"],
            "budget": [round(x) for x in budget],
            "actual": [round(x) if x is not None else None for x in actual],
            "forecast": [round(x) if x is not None else None for x in forecast],
            "variance": v, "pct_variance": p,
        }
    group_school = {
        "id": "group", "name": "Alpha Education Group (Updated)",
        "headcount": sum(s["headcount"] for s in custom_schools), "segment": "Multi-segment",
    }
    return {"school": group_school, "months": m, "actual_months": am,
            "categories": list(merged.values())}


# ── Serve frontend ──────────────────────────────────────────
_public = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "public"))

@app.get("/")
def read_index():
    path = os.path.join(_public, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"detail": f"Index not found at {path}"}

if os.path.isdir(_public):
    app.mount("/static", StaticFiles(directory=_public), name="static")

# Catch-all for other static files if not caught by Vercel
@app.get("/{path:path}")
def catch_all(path: str):
    file_path = os.path.join(_public, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(404, "Not Found")
