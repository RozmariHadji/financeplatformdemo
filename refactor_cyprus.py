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
    # Rename Region to School
    text = text.replace("RegionInput", "SchoolInput")
    text = text.replace("region_id", "school_id")
    text = text.replace("region_name", "school_name")
    text = text.replace("group_region", "group_school")
    text = text.replace("custom_regions", "custom_schools")
    text = text.replace("REGION_DATA", "SCHOOL_DATA")
    text = text.replace("REGIONS", "SCHOOLS")
    text = text.replace("Region", "School")
    text = text.replace("region", "school")
    text = text.replace("Regions", "Schools")
    text = text.replace("regions", "schools")
    
    # Update Schools data
    old_schools = """SCHOOLS = [
    {"id": "greenfield", "name": "North America",     "headcount": 650, "segment": "Secondary"},
    {"id": "oakwood",    "name": "EMEA School",          "headcount": 480, "segment": "Primary"},
    {"id": "riverside",  "name": "APAC School",       "headcount": 820, "segment": "Secondary"},
    {"id": "hillcrest",  "name": "LATAM School",       "headcount": 310, "segment": "Primary"},
    {"id": "lakeside",   "name": "Global Services",    "headcount": 520, "segment": "All-through"},
]"""
    new_schools = """SCHOOLS = [
    {"id": "pes_nicosia", "name": "Pascal English School Nicosia", "headcount": 650, "segment": "Secondary", "city": "Nicosia"},
    {"id": "pps_nicosia", "name": "Pascal Primary School Nicosia", "headcount": 480, "segment": "Primary", "city": "Nicosia"},
    {"id": "pes_limassol", "name": "Pascal English School Limassol", "headcount": 820, "segment": "Secondary", "city": "Limassol"},
    {"id": "pes_larnaca", "name": "Pascal English School Larnaca", "headcount": 520, "segment": "Secondary", "city": "Larnaca"},
]"""
    # Regex match to replace SCHOOLS array
    text = re.sub(r'SCHOOLS = \[.*?\]', new_schools, text, flags=re.DOTALL)
    text = text.replace('Global Corp (Consolidated)', 'Pascal Education Group (Consolidated)')
    text = text.replace('Global Corp (Updated)', 'Pascal Education Group (Updated)')
    text = text.replace('Global Corp', 'Pascal Education Group')

    # Add City Filtering to API
    # 1. Update group_fpna to take city
    text = text.replace("def group_fpna() -> dict:", 'def group_fpna(city: str = None) -> dict:\n    filtered_schools = [s for s in SCHOOLS if not city or city == "all" or s["city"].lower() == city.lower()]')
    text = text.replace("for school in SCHOOLS:", "for school in filtered_schools:")
    # Fix headcount sum
    text = text.replace('sum(s["headcount"] for s in SCHOOLS)', 'sum(s["headcount"] for s in filtered_schools)')
    
    # 2. Update endpoints to accept city explicitly if group
    text = text.replace('def get_fpna(school_id: str):', 'def get_fpna(school_id: str, city: str = None):')
    text = text.replace('if school_id == "group":\n        return group_fpna()', 'if school_id == "group":\n        return group_fpna(city)')
    
    text = text.replace('def get_variance(school_id: str):', 'def get_variance(school_id: str, city: str = None):')
    text = text.replace('data = group_fpna() if school_id == "group" else get_fpna(school_id)', 'data = group_fpna(city) if school_id == "group" else get_fpna(school_id)')
    
    text = text.replace('def get_schools():', 'def get_schools(city: str = None):')
    text = text.replace('for school in SCHOOLS:', 'for school in SCHOOLS:\n        if city and city != "all" and school.get("city", "").lower() != city.lower(): continue')
    
    return text

def update_js(text):
    text = text.replace("Region", "School")
    text = text.replace("region", "school")
    text = text.replace("Regions", "Schools")
    text = text.replace("regions", "schools")
    text = text.replace("Global Corp", "Pascal Education Group")
    
    # Update default schools
    new_def = """const DEF_SCHOOLS = [
  { id:'pes_nicosia', name:'Pascal English School Nicosia', headcount:650, segment:'Secondary', revenue_per_head:4500, city: 'Nicosia' },
  { id:'pps_nicosia', name:'Pascal Primary School Nicosia', headcount:480, segment:'Primary', revenue_per_head:4500, city: 'Nicosia' },
  { id:'pes_limassol', name:'Pascal English School Limassol', headcount:820, segment:'Secondary', revenue_per_head:4500, city: 'Limassol' },
  { id:'pes_larnaca', name:'Pascal English School Larnaca', headcount:520, segment:'Secondary', revenue_per_head:4500, city: 'Larnaca' },
];"""
    text = re.sub(r'const DEF_SCHOOLS = \[.*?\];', new_def, text, flags=re.DOTALL)
    
    # Add city state
    text = text.replace("school:    'group',", "school:    'group',\n  city:      'all',\n  date:      'ytd',")
    
    # Modify API calls to pass city
    text = text.replace("api(`/api/fpna/${sid}`)", "api(`/api/fpna/${sid}?city=${S.city}`)")
    text = text.replace("api('/api/schools')", "api(`/api/schools?city=${S.city}`)")
    text = text.replace("api(`/api/variance/${sid}`)", "api(`/api/variance/${sid}?city=${S.city}`)")
    
    # Add onCityChange and onDateChange events
    events = """
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
"""
    text = text.replace("function onSchoolChange(v) {", events + "\nfunction onSchoolChange(v) {")
    
    # Add date filtering logic in renderDashboard
    text = text.replace("const { months, actual_months:AM, categories } = fpna;", "let { months, actual_months:AM, categories } = fpna;\n  let max_months = S.date === 'ytd' ? AM : 12;")
    text = text.replace("slice(0,AM)", "slice(0,max_months)")
    text = text.replace("i<AM", "i<max_months")
    
    # Same for loadFpna
    text = text.replace("const { school, months, actual_months:AM, categories } = data;", "let { school, months, actual_months:AM, categories } = data;\n  let max_months = S.date === 'ytd' ? AM : 12;")
    
    return text

def update_html(text):
    text = text.replace("Global Corp", "Pascal Education Group")
    text = text.replace("Region", "School")
    text = text.replace("region", "school")
    text = text.replace("Regions", "Schools")
    text = text.replace("regions", "schools")
    text = text.replace("5 schools · 2,780 headcount", "4 schools · 2,470 headcount")
    
    # Update select dropdowns
    old_selects = """<select id="school-select" class="gt-select" onchange="onSchoolChange(this.value)">
          <option value="group">Pascal Education Group</option>
          <option value="greenfield">North America</option>
          <option value="oakwood">EMEA School</option>
          <option value="riverside">APAC School</option>
          <option value="hillcrest">LATAM School</option>
          <option value="lakeside">Global Services</option>
        </select>"""
        
    new_selects = """<div style="display: flex; gap: 8px;">
          <select id="date-select" class="gt-select" onchange="onDateChange(this.value)">
            <option value="ytd">YTD (Apr-Dec)</option>
            <option value="full">Full Year View</option>
          </select>
          <select id="city-select" class="gt-select" onchange="onCityChange(this.value)">
            <option value="all">All Cities</option>
            <option value="Nicosia">Nicosia</option>
            <option value="Limassol">Limassol</option>
            <option value="Larnaca">Larnaca</option>
          </select>
          <select id="school-select" class="gt-select" onchange="onSchoolChange(this.value)">
            <option value="group">Group Level</option>
            <option value="pes_nicosia">PES Nicosia</option>
            <option value="pps_nicosia">PPS Nicosia</option>
            <option value="pes_limassol">PES Limassol</option>
            <option value="pes_larnaca">PES Larnaca</option>
          </select>
        </div>"""
    
    text = re.sub(r'<select id="school-select".*?</select>', new_selects, text, flags=re.DOTALL)
    return text

process_file(os.path.join(DIR, "api", "index.py"), update_python)
process_file(os.path.join(DIR, "public", "js", "app.js"), update_js)
process_file(os.path.join(DIR, "public", "index.html"), update_html)

print("Refactored to Cyprus schools successfully.")
