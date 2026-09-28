import json
import os
import re
from datetime import datetime
import requests

# ==============================================================================
# 1. ENTREPRISES SURVEILLÉES VIA LEURS API ATS DIRECTES
# ==============================================================================

# Plateformes Greenhouse (Scale-ups, Licornes FR & Géants US)
GREENHOUSE_TARGETS = [
    # Licornes françaises & Européennes
    {"name": "Datadog", "token": "datadog"},
    {"name": "Mistral AI", "token": "mistralai"},
    {"name": "Ledger", "token": "ledger"},
    {"name": "Pigment", "token": "pigment"},
    {"name": "Contentsquare", "token": "contentsquare"},
    {"name": "Back Market", "token": "backmarket"},
    {"name": "Mirakl", "token": "mirakl"},
    {"name": "Spendesk", "token": "spendesk"},
    {"name": "Swile", "token": "swile"},

    # IA Générative & Cloud US
    {"name": "Anthropic", "token": "anthropic"},
    {"name": "Scale AI", "token": "scaleai"},
    {"name": "Stripe", "token": "stripe"},
    {"name": "Figma", "token": "figma"},
    {"name": "Notion", "token": "notion"},
    {"name": "Cloudflare", "token": "cloudflare"},
    {"name": "GitLab", "token": "gitlab"},
    {"name": "Vercel", "token": "vercel"},

    # Plateformes Mondiales & Fintech
    {"name": "Airbnb", "token": "airbnb"},
    {"name": "Discord", "token": "discord"},
    {"name": "Reddit", "token": "reddit"},
    {"name": "Pinterest", "token": "pinterest"},
    {"name": "Dropbox", "token": "dropbox"},
    {"name": "Coinbase", "token": "coinbase"},
    {"name": "Ramp", "token": "ramp"},
    {"name": "Brex", "token": "brex"}
]

# Plateformes Lever
LEVER_TARGETS = [
    {"name": "Spotify", "token": "spotify"},
    {"name": "Qonto", "token": "qonto"},
    {"name": "Payfit", "token": "payfit"},
    {"name": "Alan", "token": "alan"},
    {"name": "Pennylane", "token": "pennylane"},
    {"name": "Cohere", "token": "cohere"}
]

# Entreprises ciblées dans les flux communautaires Big Tech & Quant
COMMUNITY_BIGTECH_TARGETS = [
    # GAFAM & Big Tech
    "google", "microsoft", "salesforce", "meta", "apple", 
    "amazon", "palantir", "netflix", "uber", "adobe", "nvidia",
    "tesla", "snowflake", "databricks", "atlassian", "mongodb", "intel", "amd",
    
    # Quant Trading & Finance Tech d'élite
    "jane street", "citadel", "two sigma", "jump trading", 
    "hudson river trading", "optiver", "bloomberg"
]

# Flux communautaires open source vérifiés
COMMUNITY_FEEDS = [
    {
        "category": "stage",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"
    },
    {
        "category": "graduate",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
    }
]

STUDENT_KEYWORDS = [
    "intern", "internship", "stage", "stagiaire", "pfe",
    "graduate", "grad", "early career", "rotational",
    "alternan", "alternance", "apprenti", "apprentissage",
    "junior", "associate"
]

JOBS_FILE = "jobs.json"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==============================================================================
# 2. FONCTIONS DE FILTRAGE ET ANALYSE
# ==============================================================================
def is_student_job(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in STUDENT_KEYWORDS)

def detect_category(title: str, default_cat: str = "cdi") -> str:
    t = title.lower()
    if any(k in t for k in ["graduate", "rotational", "early career", "new grad"]):
        return "graduate"
    if any(k in t for k in ["alternan", "apprenti", "apprentissage"]):
        return "alternance"
    if any(k in t for k in ["intern", "stage", "pfe", "stagiaire"]):
        return "stage"
    return default_cat

def extract_tags(title: str) -> list:
    known_tags = [
        "Python", "Go", "Golang", "Java", "C++", "Rust", "TypeScript", 
        "JavaScript", "React", "Node", "Backend", "Frontend", "Fullstack",
        "Data", "AI", "Machine Learning", "LLM", "DevOps", "Cloud", 
        "Security", "Cyber", "Product", "Mobile", "iOS", "Android", "Quant"
    ]
    tags = []
    for tag in known_tags:
        if re.search(r'\b' + re.escape(tag) + r'\b', title, re.IGNORECASE):
            tags.append(tag)
    return tags if tags else ["Tech"]

# ==============================================================================
# 3. COLLECTE DES OFFRES
# ==============================================================================
def fetch_community_jobs():
    jobs = []
    for feed in COMMUNITY_FEEDS:
        try:
            res = requests.get(feed["url"], headers=REQUEST_HEADERS, timeout=12)
            if res.status_code == 200:
                data = res.json()
                for item in data:
                    comp_name = item.get("company_name", "").strip()
                    comp_lower = comp_name.lower()

                    if any(target in comp_lower for target in COMMUNITY_BIGTECH_TARGETS):
                        if not item.get("active", True):
                            continue

                        locations = item.get("locations", [])
                        loc_str = ", ".join(locations[:2]) if isinstance(locations, list) else str(locations)

                        jobs.append({
                            "id": f"comm_{comp_lower[:4]}_{abs(hash(item.get('url', '')))}",
                            "title": item.get("title", "").strip(),
                            "company": comp_name,
                            "category": detect_category(item.get("title", ""), default_cat=feed["category"]),
                            "status": "open",
                            "location": loc_str if loc_str else "International / Multi",
                            "url": item.get("url"),
                            "tags": extract_tags(item.get("title", ""))
                        })
        except Exception as e:
            print(f"[!] Erreur sur le flux communautaire ({feed['category']}): {e}")
    return jobs

def fetch_greenhouse_jobs(company: str, token: str) -> list:
    jobs = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
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

def fetch_lever_jobs(company: str, token: str) -> list:
    jobs = []
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
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

# ==============================================================================
# 4. SYNCHRONISATION GLOBALE
# ==============================================================================
def main():
    now_str = datetime.now().strftime("%d/%m/%Y")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Démarrage de la synchronisation étendue...")

    old_jobs = {}
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                for j in json.load(f):
                    old_jobs[j["id"]] = j
        except Exception as e:
            print(f"[!] Impossible de charger {JOBS_FILE}: {e}")

    current_seen_ids = set()
    updated_jobs = []

    # 1. Collecte Big Tech & Quant (Google, Meta, Jane Street, Citadel...)
    print("-> Scan Big Tech & Quant Trading...")
    for job in fetch_community_jobs():
        current_seen_ids.add(job["id"])
        is_new = job["id"] not in old_jobs
        job["first_seen"] = old_jobs[job["id"]]["first_seen"] if not is_new else now_str
        updated_jobs.append(job)

    # 2. Collecte Greenhouse (Datadog, Anthropic, Mistral, Scale AI, Pigment...)
    print("-> Scan des plateformes Greenhouse...")
    for comp in GREENHOUSE_TARGETS:
        for job in fetch_greenhouse_jobs(comp["name"], comp["token"]):
            if is_student_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_category(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_tags(job["title"]),
                    "first_seen": old_jobs[job["id"]]["first_seen"] if not is_new else now_str
                })

    # 3. Collecte Lever (Spotify, Qonto, Alan, Pennylane, Payfit...)
    print("-> Scan des plateformes Lever...")
    for comp in LEVER_TARGETS:
        for job in fetch_lever_jobs(comp["name"], comp["token"]):
            if is_student_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_category(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_tags(job["title"]),
                    "first_seen": old_jobs[job["id"]]["first_seen"] if not is_new else now_str
                })

    # 4. Identification des offres fermées
    for old_id, old_job in old_jobs.items():
        if old_id not in current_seen_ids:
            old_job["status"] = "closed"
            updated_jobs.append(old_job)

    # Écriture dans jobs.json
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_jobs, f, indent=2, ensure_ascii=False)

    open_total = sum(1 for j in updated_jobs if j["status"] == "open")
    closed_total = sum(1 for j in updated_jobs if j["status"] == "closed")
    print(f"[✓] Terminé avec succès : {open_total} postes ouverts et {closed_total} archivés sur plus de 60 entreprises.")

if __name__ == "__main__":
    main()
