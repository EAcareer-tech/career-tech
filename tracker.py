import json
import os
import re
from datetime import datetime
import requests

# ==============================================================================
# 1. ENTREPRISES CIBLES AVEC FORTE ACTIVITÉ TECH SALES / SDR / BDR
# ==============================================================================
GREENHOUSE_TARGETS = [
    # Licornes & Scale-ups France (Très fortes équipes Sales à Paris)
    {"name": "Datadog", "token": "datadog"},
    {"name": "Alan", "token": "alan"},
    {"name": "Contentsquare", "token": "contentsquare"},
    {"name": "Pigment", "token": "pigment"},
    {"name": "Swile", "token": "swile"},
    {"name": "Spendesk", "token": "spendesk"},
    {"name": "Mirakl", "token": "mirakl"},
    {"name": "Pennylane", "token": "pennylane"},
    {"name": "Malt", "token": "malt"},

    # Géants du SaaS & International
    {"name": "Stripe", "token": "stripe"},
    {"name": "Notion", "token": "notion"},
    {"name": "Figma", "token": "figma"},
    {"name": "HubSpot", "token": "hubspot"},
    {"name": "Miro", "token": "miro"},
    {"name": "Snowflake", "token": "snowflake"},
    {"name": "Databricks", "token": "databricks"},
    {"name": "Cloudflare", "token": "cloudflare"},
    {"name": "GitLab", "token": "gitlab"},
    {"name": "Vercel", "token": "vercel"}
]

LEVER_TARGETS = [
    {"name": "Qonto", "token": "qonto"},
    {"name": "Payfit", "token": "payfit"},
    {"name": "Spotify", "token": "spotify"}
]

SMARTRECRUITERS_TARGETS = [
    {"name": "Doctolib", "token": "doctolib"}
]

# Géants Tech recrutant massivement en Sales Graduates (via flux communautaire)
COMMUNITY_SALES_TARGETS = [
    "salesforce", "oracle", "cisco", "bloomberg", "aws", "amazon",
    "microsoft", "google", "sap", "servicenow", "adobe", "workday"
]

COMMUNITY_FEEDS = [
    {
        "category": "graduate",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
    },
    {
        "category": "stage",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"
    }
]

# Mots-clés OBLIGATOIRES pour qualifier une offre commerciale
SALES_KEYWORDS = [
    "sdr", "bdr", "sales development", "business development", 
    "inside sales", "account executive", "commercial", "sales intern", 
    "sales representative", "sales graduate", "sales academy",
    "account manager", "growth sales", "sales trainee", "solution sales"
]

# Exclusion stricte des profils de développement et d'ingénierie technique
EXCLUDE_KEYWORDS = [
    "software engineer", "developer", "backend", "frontend", "fullstack",
    "devops", "qa engineer", "infrastructure", "machine learning", "deep learning",
    "hardware", "firmware", "site reliability", "security engineer"
]

JOBS_FILE = "jobs.json"

# ==============================================================================
# 2. FILTRES SPÉCIALISÉS SALES
# ==============================================================================
def is_sales_job(title: str) -> bool:
    t = title.lower()
    
    # 1. Vérifier si un terme technique à exclure est présent
    if any(ex in t for ex in EXCLUDE_KEYWORDS):
        return False
        
    # 2. Vérifier si un rôle commercial est explicitement mentionné
    return any(sk in t for sk in SALES_KEYWORDS)

def detect_contract(title: str, default_cat: str = "cdi") -> str:
    t = title.lower()
    if any(k in t for k in ["graduate", "rotational", "early career", "academy", "program"]):
        return "graduate"
    if any(k in t for k in ["alternan", "apprenti", "apprentissage"]):
        return "alternance"
    if any(k in t for k in ["intern", "stage", "pfe", "stagiaire", "trainee"]):
        return "stage"
    return default_cat

def extract_sales_tags(title: str) -> list:
    tags = []
    t = title.lower()
    if "sdr" in t or "sales development" in t:
        tags.append("SDR")
    if "bdr" in t or "business development" in t:
        tags.append("BDR")
    if "inbound" in t:
        tags.append("Inbound")
    if "outbound" in t:
        tags.append("Outbound")
    if "account executive" in t or "ae" in t:
        tags.append("Account Executive")
    if "graduate" in t or "academy" in t:
        tags.append("Graduate Track")
    if not tags:
        tags = ["Tech Sales", "B2B SaaS"]
    return tags

# ==============================================================================
# 3. EXTRACTIONS DES PLATEFORMES CARRIÈRES
# ==============================================================================
def fetch_greenhouse(company: str, token: str) -> list:
    jobs = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobs", []):
                jobs.append({
                    "id": f"gh_{token}_{item.get('id')}",
                    "title": item.get("title", "").strip(),
                    "company": company,
                    "location": (item.get("location") or {}).get("name", "Non précisé").strip(),
                    "url": item.get("absolute_url")
                })
    except Exception as e:
        print(f"[!] Erreur Greenhouse ({company}): {e}")
    return jobs

def fetch_lever(company: str, token: str) -> list:
    jobs = []
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json():
                cat = item.get("categories", {})
                jobs.append({
                    "id": f"lev_{token}_{item.get('id')}",
                    "title": item.get("text", "").strip(),
                    "company": company,
                    "location": cat.get("location", "Non précisé").strip(),
                    "url": item.get("hostedUrl")
                })
    except Exception as e:
        print(f"[!] Erreur Lever ({company}): {e}")
    return jobs

def fetch_smartrecruiters(company: str, token: str) -> list:
    jobs = []
    url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("content", []):
                loc = item.get("location", {})
                loc_str = f"{loc.get('city', '')}, {loc.get('country', '')}".strip(", ")
                jobs.append({
                    "id": f"sr_{token}_{item.get('id')}",
                    "title": item.get("name", "").strip(),
                    "company": company,
                    "location": loc_str if loc_str else "Paris, France",
                    "url": f"https://jobs.smartrecruiters.com/{token}/{item.get('id')}"
                })
    except Exception as e:
        print(f"[!] Erreur SmartRecruiters ({company}): {e}")
    return jobs

def fetch_community_sales() -> list:
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for feed in COMMUNITY_FEEDS:
        try:
            res = requests.get(feed["url"], headers=headers, timeout=12)
            if res.status_code == 200:
                for item in res.json():
                    comp = item.get("company_name", "").strip()
                    title = item.get("title", "").strip()
                    if any(target in comp.lower() for target in COMMUNITY_SALES_TARGETS) and is_sales_job(title):
                        if not item.get("active", True):
                            continue
                        locs = item.get("locations", [])
                        loc_str = ", ".join(locs[:2]) if isinstance(locs, list) else str(locs)
                        jobs.append({
                            "id": f"comm_{comp[:4].lower()}_{abs(hash(item.get('url', '')))}",
                            "title": title,
                            "company": comp,
                            "category": detect_contract(title, default_cat=feed["category"]),
                            "status": "open",
                            "location": loc_str if loc_str else "International",
                            "url": item.get("url"),
                            "tags": extract_sales_tags(title)
                        })
        except Exception as e:
            print(f"[!] Erreur flux communautaire : {e}")
    return jobs

# ==============================================================================
# 4. SYNCHRONISATION
# ==============================================================================
def main():
    now_str = datetime.now().strftime("%d/%m/%Y")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lancement du scan 100% TECH SALES...")

    old_jobs = {}
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                for j in json.load(f):
                    old_jobs[j["id"]] = j
        except Exception as e:
            print(f"[!] Erreur de lecture : {e}")

    current_seen_ids = set()
    updated_jobs = []

    # 1. Greenhouse
    for comp in GREENHOUSE_TARGETS:
        for job in fetch_greenhouse(comp["name"], comp["token"]):
            if is_sales_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_contract(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_sales_tags(job["title"]),
                    "first_seen": old_jobs[job["id"]]["first_seen"] if not is_new else now_str
                })

    # 2. Lever
    for comp in LEVER_TARGETS:
        for job in fetch_lever(comp["name"], comp["token"]):
            if is_sales_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_contract(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_sales_tags(job["title"]),
                    "first_seen": old_jobs[job["id"]]["first_seen"] if not is_new else now_str
                })

    # 3. SmartRecruiters (Doctolib)
    for comp in SMARTRECRUITERS_TARGETS:
        for job in fetch_smartrecruiters(comp["name"], comp["token"]):
            if is_sales_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_contract(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_sales_tags(job["title"]),
                    "first_seen": old_jobs[job["id"]]["first_seen"] if not is_new else now_str
                })

    # 4. Big Tech Sales Graduates
    for job in fetch_community_sales():
        current_seen_ids.add(job["id"])
        is_new = job["id"] not in old_jobs
        job["first_seen"] = old_jobs[job["id"]]["first_seen"] if not is_new else now_str
        updated_jobs.append(job)

    # 5. Détection des postes retirés
    for old_id, old_job in old_jobs.items():
        if old_id not in current_seen_ids:
            old_job["status"] = "closed"
            updated_jobs.append(old_job)

    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_jobs, f, indent=2, ensure_ascii=False)

    print(f"[✓] Terminé : {len(updated_jobs)} opportunités Tech Sales synchronisées.")

if __name__ == "__main__":
    main()
