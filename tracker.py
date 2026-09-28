import json
import os
import re
from datetime import datetime
import requests

# ==============================================================================
# CONFIGURATION DES ENTREPRISES CIBLES (API ATS DIRECTES)
# ==============================================================================
# Greenhouse Boards (api.greenhouse.io/v1/boards/{token}/jobs)
GREENHOUSE_TARGETS = [
    {"name": "Datadog", "token": "datadog"},
    {"name": "Stripe", "token": "stripe"},
    {"name": "Figma", "token": "figma"},
    {"name": "Cloudflare", "token": "cloudflare"},
    {"name": "Mistral AI", "token": "mistralai"},
    {"name": "GitLab", "token": "gitlab"},
    {"name": "Vercel", "token": "vercel"},
    {"name": "Deliveroo", "token": "deliveroo"},
    {"name": "Notion", "token": "notion"}
]

# Lever Boards (api.lever.co/v0/postings/{token}?mode=json)
LEVER_TARGETS = [
    {"name": "Spotify", "token": "spotify"},
    {"name": "Qonto", "token": "qonto"},
    {"name": "Payfit", "token": "payfit"}
]

# Mots-clés de détection pour profils étudiants et débutants
STUDENT_KEYWORDS = [
    "intern", "internship", "stage", "stagiaire", "pfe",
    "graduate", "grad", "early career", "rotational",
    "alternan", "alternance", "apprenti", "apprentissage",
    "junior", "associate"
]

JOBS_FILE = "jobs.json"

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================
def is_student_job(title: str) -> bool:
    """Vérifie si le titre correspond à une opportunité étudiante ou jeune diplômé."""
    title_clean = title.lower()
    return any(keyword in title_clean for keyword in STUDENT_KEYWORDS)

def detect_category(title: str) -> str:
    """Catégorise l'offre selon le type de contrat recherché."""
    t = title.lower()
    if any(k in t for k in ["graduate", "rotational", "early career"]):
        return "graduate"
    if any(k in t for k in ["alternan", "apprenti", "apprentissage"]):
        return "alternance"
    if any(k in t for k in ["intern", "stage", "pfe", "stagiaire"]):
        return "stage"
    return "cdi"

def extract_tags(title: str) -> list:
    """Extrait des tags techniques courants du titre."""
    known_tags = [
        "Python", "Go", "Golang", "Java", "C++", "Rust", "TypeScript", 
        "JavaScript", "React", "Node", "Backend", "Frontend", "Fullstack",
        "Data", "AI", "Machine Learning", "LLM", "DevOps", "Cloud", 
        "Security", "Cyber", "Product", "Mobile", "iOS", "Android"
    ]
    tags = []
    for tag in known_tags:
        if re.search(r'\b' + re.escape(tag) + r'\b', title, re.IGNORECASE):
            tags.append(tag)
    return tags if tags else ["Tech"]

# ==============================================================================
# EXTRACTION DES FLUX D'ENTREPRISES
# ==============================================================================
def fetch_greenhouse(company: str, token: str) -> list:
    jobs = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            data = res.json().get("jobs", [])
            for item in data:
                jobs.append({
                    "id": f"gh_{token}_{item.get('id')}",
                    "title": item.get("title", "").strip(),
                    "company": company,
                    "location": (item.get("location") or {}).get("name", "Non précisé").strip(),
                    "url": item.get("absolute_url")
                })
    except Exception as e:
        print(f"[!] Erreur Greenhouse pour {company}: {e}")
    return jobs

def fetch_lever(company: str, token: str) -> list:
    jobs = []
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                cat = item.get("categories", {})
                jobs.append({
                    "id": f"lev_{token}_{item.get('id')}",
                    "title": item.get("text", "").strip(),
                    "company": company,
                    "location": cat.get("location", "Non précisé").strip(),
                    "url": item.get("hostedUrl")
                })
    except Exception as e:
        print(f"[!] Erreur Lever pour {company}: {e}")
    return jobs

# ==============================================================================
# SYNCHRONISATION ET GESTION DU CYCLE DE VIE DES OFFRES
# ==============================================================================
def main():
    now_str = datetime.now().strftime("%d/%m/%Y")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Lancement du scan des carrières tech...")

    # Chargement de la base existante
    old_jobs = {}
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                for j in json.load(f):
                    old_jobs[j["id"]] = j
        except Exception as e:
            print(f"[!] Erreur lors de la lecture de {JOBS_FILE}: {e}")

    current_seen_ids = set()
    updated_jobs = []

    # 1. Analyse Greenhouse
    for comp in GREENHOUSE_TARGETS:
        for job in fetch_greenhouse(comp["name"], comp["token"]):
            if is_student_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                first_seen = old_jobs[job["id"]]["first_seen"] if not is_new else now_str

                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_category(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_tags(job["title"]),
                    "first_seen": first_seen
                })

    # 2. Analyse Lever
    for comp in LEVER_TARGETS:
        for job in fetch_lever(comp["name"], comp["token"]):
            if is_student_job(job["title"]):
                current_seen_ids.add(job["id"])
                is_new = job["id"] not in old_jobs
                first_seen = old_jobs[job["id"]]["first_seen"] if not is_new else now_str

                updated_jobs.append({
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "category": detect_category(job["title"]),
                    "status": "open",
                    "location": job["location"],
                    "url": job["url"],
                    "tags": extract_tags(job["title"]),
                    "first_seen": first_seen
                })

    # 3. Détection des offres fermées / retirées par les entreprises
    for old_id, old_job in old_jobs.items():
        if old_id not in current_seen_ids:
            old_job["status"] = "closed"
            updated_jobs.append(old_job)

    # Sauvegarde dans jobs.json
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_jobs, f, indent=2, ensure_ascii=False)

    open_count = sum(1 for j in updated_jobs if j["status"] == "open")
    closed_count = sum(1 for j in updated_jobs if j["status"] == "closed")
    print(f"[✓] Terminé avec succès : {open_count} offres ouvertes et {closed_count} archivées dans {JOBS_FILE}.")

if __name__ == "__main__":
    main()
