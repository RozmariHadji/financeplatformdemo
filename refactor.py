import os
import re

DIR = r"c:\Users\r.hadjicharalambous\OneDrive - Grant Thornton Cyprus\Desktop\PascalExample"

def process_file(path, func):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = func(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def update_html(text):
    text = text.replace("Academy Trust Group", "Global Corp")
    text = text.replace("5 schools · 2,780 pupils", "5 regions · 2,780 headcount")
    text = text.replace("Greenfield Academy", "North America")
    text = text.replace("Oakwood School", "EMEA Region")
    text = text.replace("Riverside College", "APAC Region")
    text = text.replace("Hillcrest Primary", "LATAM Region")
    text = text.replace("Lakeside Free School", "Global Services")
    
    text = text.replace("SCHOOL", "REGION")
    text = text.replace("School", "Region").replace("school", "region")
    text = text.replace("Schools", "Regions").replace("schools", "regions")
    text = text.replace("Pupils", "Headcount").replace("pupils", "headcount")
    text = text.replace("Phase", "Segment").replace("phase", "segment")
    
    # Fix double-replacements if any
    text = text.replace("Per-Headcount Rate", "Rev per Head")
    text = text.replace("Projected GAG", "Projected Revenue")
    text = text.replace("GAG", "Revenue")
    
    # Replace purple with primary
    text = text.replace("purple", "primary")
    
    # Remove FP&A Engine and AI Insights tabs from sidebar
    text = re.sub(r'<button class="nav-item" data-tab="fpna".*?</button>', '', text, flags=re.DOTALL)
    text = re.sub(r'<button class="nav-item" data-tab="ai".*?</button>', '', text, flags=re.DOTALL)
    
    # Remove AI Insights and FPNA sections
    text = re.sub(r'<!-- ═══ FP&A ENGINE ═══ -->.*?<!-- ═══ AI INSIGHTS ═══ -->', '<!-- ═══ AI INSIGHTS ═══ -->', text, flags=re.DOTALL)
    text = re.sub(r'<!-- ═══ AI INSIGHTS ═══ -->\s*<section id="tab-ai" class="tab-content">.*?</section>', '', text, flags=re.DOTALL)
    
    # Rename GEWiz
    text = text.replace("GEWiz", "FinWiz")
    return text

def update_css(text):
    text = text.replace("purple", "primary")
    text = re.sub(r'--primary:\s*#[0-9a-fA-F]+;', '--primary:        #0F172A;', text)
    text = re.sub(r'--primary-dark:\s*#[0-9a-fA-F]+;', '--primary-dark:   #020617;', text)
    text = re.sub(r'--primary-xdark:\s*#[0-9a-fA-F]+;', '--primary-xdark:  #0B0F19;', text)
    text = re.sub(r'--primary-light:\s*#[0-9a-fA-F]+;', '--primary-light:  #334155;', text)
    text = re.sub(r'--primary-tint:\s*#[0-9a-fA-F]+;', '--primary-tint:   #F1F5F9;', text)
    text = re.sub(r'--primary-faint:\s*#[0-9a-fA-F]+;', '--primary-faint:  #F8FAFC;', text)
    text = re.sub(r'--bg:\s*#[0-9a-fA-F]+;', '--bg:            #FAFBFC;', text)
    
    text = text.replace("#4B2882", "var(--primary)")
    text = text.replace("#3B4CB8", "var(--primary-light)")
    text = text.replace("#5D3599", "#1E293B")
    return text

def update_js(text):
    text = text.replace("Academy Trust Group", "Global Corp")
    text = text.replace("Greenfield Academy", "North America")
    text = text.replace("Oakwood School", "EMEA Region")
    text = text.replace("Riverside College", "APAC Region")
    text = text.replace("Hillcrest Primary", "LATAM Region")
    text = text.replace("Lakeside Free School", "Global Services")
    
    text = text.replace("SCHOOL", "REGION")
    text = text.replace("School", "Region").replace("school", "region")
    text = text.replace("Schools", "Regions").replace("schools", "regions")
    text = text.replace("Pupils", "Headcount").replace("pupils", "headcount")
    text = text.replace("Phase", "Segment").replace("phase", "segment")
    
    text = text.replace("gag_funding", "core_revenue")
    text = text.replace("gagC", "core_revC")
    text = text.replace("gag-row", "rev-row")
    
    text = text.replace("teaching_staff", "direct_labor")
    text = text.replace("Teaching Staff", "Direct Labor")
    text = text.replace("support_staff", "indirect_labor")
    text = text.replace("Support Staff", "Indirect Labor")
    text = text.replace("leadership", "management")
    text = text.replace("Leadership & Management", "Management & Execs")
    text = text.replace("premises", "facilities")
    text = text.replace("Premises & Facilities", "Facilities & Utilities")
    text = text.replace("administration", "admin")
    text = text.replace("Administration", "Admin & Overhead")
    text = text.replace("resources", "software")
    text = text.replace("Resources & Supplies", "Software & Tools")
    text = text.replace("funding_rate", "revenue_per_head")
    
    text = text.replace("purple", "primary")
    text = text.replace("#4B2882", "#0F172A")
    text = text.replace("#5D3599", "#1E293B")
    text = text.replace("#3B4CB8", "#334155")
    
    return text

def update_py(text):
    text = text.replace("Academy Trust Group", "Global Corp")
    text = text.replace("Greenfield Academy", "North America")
    text = text.replace("Oakwood School", "EMEA Region")
    text = text.replace("Riverside College", "APAC Region")
    text = text.replace("Hillcrest Primary", "LATAM Region")
    text = text.replace("Lakeside Free School", "Global Services")
    
    text = text.replace("SCHOOL", "REGION")
    text = text.replace("School", "Region").replace("school", "region")
    text = text.replace("Schools", "Regions").replace("schools", "regions")
    text = text.replace("Pupils", "Headcount").replace("pupils", "headcount")
    text = text.replace("Phase", "Segment").replace("phase", "segment")
    
    text = text.replace("gag_funding", "core_revenue")
    text = text.replace("GAG Funding", "Core Revenue")
    text = text.replace("gag ", "core_rev ")
    text = text.replace("gag =", "core_rev =")
    
    text = text.replace("teaching_staff", "direct_labor")
    text = text.replace("Teaching Staff", "Direct Labor")
    text = text.replace("support_staff", "indirect_labor")
    text = text.replace("Support Staff", "Indirect Labor")
    text = text.replace("leadership", "management")
    text = text.replace("Leadership & Management", "Management & Execs")
    text = text.replace("premises", "facilities")
    text = text.replace("Premises & Facilities", "Facilities & Utilities")
    text = text.replace("administration", "admin")
    text = text.replace("Administration", "Admin & Overhead")
    text = text.replace("resources", "software")
    text = text.replace("Resources & Supplies", "Software & Tools")
    
    text = text.replace("funding_rate", "revenue_per_head")
    return text

process_file(os.path.join(DIR, "public", "index.html"), update_html)
process_file(os.path.join(DIR, "public", "css", "styles.css"), update_css)
process_file(os.path.join(DIR, "public", "js", "app.js"), update_js)
process_file(os.path.join(DIR, "api", "index.py"), update_py)

print("Refactor completed successfully!")
