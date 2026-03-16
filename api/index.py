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
gemini_model = None
try:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key and api_key != "your_gemini_api_key_here":
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
except Exception:
    pass

# ── Synthetic data ───────────────────────────────────────────────────────────
MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
ACTUAL_MONTHS = 9  # Apr–Dec 2025 have actuals; Jan–Mar 2026 are forecast

SCHOOLS = [
    {"id": "greenfield", "name": "Greenfield Academy",     "pupils": 650, "phase": "Secondary"},
    {"id": "oakwood",    "name": "Oakwood School",          "pupils": 480, "phase": "Primary"},
    {"id": "riverside",  "name": "Riverside College",       "pupils": 820, "phase": "Secondary"},
    {"id": "hillcrest",  "name": "Hillcrest Primary",       "pupils": 310, "phase": "Primary"},
    {"id": "lakeside",   "name": "Lakeside Free School",    "pupils": 520, "phase": "All-through"},
]

CATEGORIES = [
    {"key": "gag_funding",    "label": "GAG Funding",              "type": "revenue"},
    {"key": "other_income",   "label": "Other Income",             "type": "revenue"},
    {"key": "teaching_staff", "label": "Teaching Staff",           "type": "expenditure"},
    {"key": "support_staff",  "label": "Support Staff",            "type": "expenditure"},
    {"key": "leadership",     "label": "Leadership & Management",  "type": "expenditure"},
    {"key": "premises",       "label": "Premises & Facilities",    "type": "expenditure"},
    {"key": "administration", "label": "Administration",           "type": "expenditure"},
    {"key": "resources",      "label": "Resources & Supplies",     "type": "expenditure"},
    {"key": "other_costs",    "label": "Other Costs",              "type": "expenditure"},
]

# Revenue and expenditure share of GAG per category
BUDGET_RATIOS = {
    "gag_funding":    1.00,
    "other_income":   0.05,
    "teaching_staff": 0.45,
    "support_staff":  0.15,
    "leadership":     0.08,
    "premises":       0.08,
    "administration": 0.06,
    "resources":      0.04,
    "other_costs":    0.03,
}

# Monthly seasonality weights (Apr to Mar)
SEASONALITY_REV = [1.0, 1.0, 0.95, 0.70, 0.70, 1.05, 1.05, 1.05, 1.05, 1.0, 1.0, 0.90]
SEASONALITY_EXP = [1.0, 1.0, 0.95, 0.60, 0.60, 1.10, 1.10, 1.10, 1.00, 1.0, 1.0, 0.95]


def annual_budget(pupils: int, key: str) -> float:
    gag = pupils * 4500
    return gag * BUDGET_RATIOS.get(key, 0)


def gen_school(school: dict, seed: int) -> dict:
    rng = random.Random(seed)
    result = {}
    for cat in CATEGORIES:
        key = cat["key"]
        typ = cat["type"]
        annual = annual_budget(school["pupils"], key)
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
        annual = annual_budget(school["pupils"], key)
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


def build_fpna(school: dict, sdata: dict) -> dict:
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
    return {"school": school, "months": MONTHS, "actual_months": ACTUAL_MONTHS, "categories": cats}


def group_fpna() -> dict:
    merged = {}
    for cat in CATEGORIES:
        key = cat["key"]
        budget = [0] * 12
        actual = [None] * 12
        forecast = [None] * 12
        for school in SCHOOLS:
            d = SCHOOL_DATA[school["id"]][key]
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
        "id": "group",
        "name": "Academy Trust Group (Consolidated)",
        "pupils": sum(s["pupils"] for s in SCHOOLS),
        "phase": "Multi-phase",
    }
    return {"school": group_school, "months": MONTHS, "actual_months": ACTUAL_MONTHS,
            "categories": list(merged.values())}


# ── API routes ────────────────────────────────────────────────────────────────
@app.get("/api/schools")
def get_schools():
    out = []
    for school in SCHOOLS:
        sid = school["id"]
        sd = SCHOOL_DATA[sid]
        rev_b = rev_a = exp_b = exp_a = 0
        for cat in CATEGORIES:
            key = cat["key"]
            for i in range(ACTUAL_MONTHS):
                b = sd[key]["budget"][i]
                a = sd[key]["actual"][i] or b
                if cat["type"] == "revenue":
                    rev_b += b; rev_a += a
                else:
                    exp_b += b; exp_a += a
        out.append({**school,
                    "ytd_revenue_budget": round(rev_b),
                    "ytd_revenue_actual": round(rev_a),
                    "ytd_expenditure_budget": round(exp_b),
                    "ytd_expenditure_actual": round(exp_a),
                    "ytd_surplus_budget": round(rev_b - exp_b),
                    "ytd_surplus_actual": round(rev_a - exp_a),
                    "erp_status": "Connected", "erp_system": "SIMS"})
    return {"schools": out, "months": MONTHS, "actual_months": ACTUAL_MONTHS}


@app.get("/api/fpna/{school_id}")
def get_fpna(school_id: str):
    if school_id == "group":
        return group_fpna()
    school = next((s for s in SCHOOLS if s["id"] == school_id), None)
    if not school:
        raise HTTPException(404, "School not found")
    return build_fpna(school, SCHOOL_DATA[school_id])


@app.get("/api/variance/{school_id}")
def get_variance(school_id: str):
    data = group_fpna() if school_id == "group" else get_fpna(school_id)
    significant = []
    for cat in data["categories"]:
        b_ytd = sum(cat["budget"][:ACTUAL_MONTHS])
        a_ytd = sum(x for x in cat["actual"][:ACTUAL_MONTHS] if x is not None)
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
        "actual_months": ACTUAL_MONTHS,
        "months": MONTHS[:ACTUAL_MONTHS],
    }


@app.get("/api/consolidation")
def get_consolidation():
    rows = []
    for s in SCHOOLS:
        rev = sum(annual_budget(s["pupils"], c["key"]) for c in CATEGORIES if c["type"] == "revenue")
        exp = sum(annual_budget(s["pupils"], c["key"]) for c in CATEGORIES if c["type"] == "expenditure")
        rows.append({"school": s["name"], "pupils": s["pupils"],
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
    if not gemini_model:
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
        resp = gemini_model.generate_content(prompt)
        max_pct = max((abs(v["pct_variance"]) for v in req.variances), default=0)
        risk = "High" if max_pct > 10 else "Medium" if max_pct > 5 else "Low"
        return {"explanation": resp.text,
                "key_drivers": [v["category"] for v in req.variances[:3]],
                "risk_rating": risk}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/ai/board-commentary")
def board_commentary(req: CommentaryRequest):
    if not gemini_model:
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
        resp = gemini_model.generate_content(prompt)
        return {"commentary": resp.text}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Recalculate with custom assumptions ──────────────────────────────────────
class SchoolInput(BaseModel):
    id: str
    name: str
    pupils: int
    phase: str
    funding_rate: float = 4500


class RecalcRequest(BaseModel):
    schools: list
    ratios: dict


def generate_custom_data(school: dict, seed: int, ratios: dict, funding_rate: float) -> dict:
    rng = random.Random(seed)
    result = {}
    gag = school["pupils"] * funding_rate
    for cat in CATEGORIES:
        key = cat["key"]
        typ = cat["type"]
        if key == "gag_funding":
            annual = gag
        elif key == "other_income":
            annual = gag * 0.05
        else:
            annual = gag * ratios.get(key, BUDGET_RATIOS.get(key, 0))
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
        s["id"]: generate_custom_data(s, 42 + i * 7, custom_ratios, s.get("funding_rate", 4500))
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
        "id": "group", "name": "Academy Trust Group (Updated)",
        "pupils": sum(s["pupils"] for s in custom_schools), "phase": "Multi-phase",
    }
    return {"school": group_school, "months": MONTHS, "actual_months": ACTUAL_MONTHS,
            "categories": list(merged.values())}


# ── Serve frontend (local dev only) ──────────────────────────────────────────
_public = os.path.join(os.path.dirname(__file__), "..", "public")
if os.path.isdir(_public):
    app.mount("/", StaticFiles(directory=_public, html=True), name="static")
