"""
Quick test: run scripts 02 + 03 logic on 5 companies from master_companies.csv
to verify output quality before the full run.

Outputs saved to pipeline/output/test_careers.csv and test_enriched.csv
(does NOT touch the real output CSVs).

Run with:
    python test_run.py
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

BASE       = Path(__file__).parent.parent
MASTER_CSV = BASE / "pipeline" / "output" / "master_companies.csv"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # export OPENAI_API_KEY=sk-...
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()
MODEL  = "gpt-4o-mini"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

import re
CAREERS_KEYWORDS = re.compile(
    r'\b(careers?|jobs?|vacancies|openings?|hiring|join us|join the team)\b',
    re.IGNORECASE
)

def fetch_html(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout, headers=HEADERS, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        for t in soup(["script", "style", "nav", "footer", "header"]):
            t.decompose()
        return soup.get_text(separator=" ", strip=True), soup
    except Exception:
        return None, None

def find_careers_links(base_url, soup):
    from urllib.parse import urljoin, urlparse
    base_domain = urlparse(base_url).netloc
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        label = a["href"] + " " + a.get_text(strip=True)
        if CAREERS_KEYWORDS.search(label):
            full = urljoin(base_url, a["href"])
            if urlparse(full).netloc == base_domain and full not in seen:
                seen.add(full)
                out.append(full)
    return sorted(out, key=len)[:5]

def gpt_careers(name, url, careers_url, text):
    prompt = f"""Company: {name}
Page URL: {careers_url or url}
Page text:
---
{text[:10000]}
---
Return JSON only:
{{
  "has_careers_page": true/false,
  "roles": [{{"title":"...","type":"...","location":"...","url":"..."}}],
  "contact_email": null,
  "apply_url": null,
  "summary": "..."
}}"""
    try:
        r = client.chat.completions.create(model=MODEL,
            messages=[{"role":"user","content":prompt}],
            temperature=0, max_tokens=600,
            response_format={"type":"json_object"})
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

def gpt_enrich(name, url, sic, homepage_text):
    prompt = f"""Company: {name}
URL: {url or "unknown"}
SIC: {sic or "unknown"}
Homepage text:
---
{(homepage_text or "")[:6000]}
---
Return JSON only:
{{
  "description": "2-3 sentence summary",
  "sector_tags": ["tag1","tag2"],
  "stage": "startup|scaleup|established|unknown",
  "tech_keywords": "...",
  "employee_est": "1-10|11-50|51-200|200-1000|1000+|unknown",
  "hiring_status": "actively_hiring|possibly_hiring|no_info",
  "founded_year": null
}}"""
    try:
        r = client.chat.completions.create(model=MODEL,
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=450,
            response_format={"type":"json_object"})
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

# ── Test ──────────────────────────────────────────────────────────────────────
master = pd.read_csv(MASTER_CSV)

# Pick 5 varied test companies: 2 well-known, 1 CH-only (no URL), 2 mid-size
# Try to pick ones with real websites likely to have careers pages
TEST_COMPANIES = ["Gearset", "Riverlane", "Nyobolt", "Echion Technologies", "Collabora Ltd"]

test_rows = master[master["company_name"].isin(TEST_COMPANIES)].drop_duplicates("company_name")
# If any aren't in the master (shouldn't happen), fall back to first 5 with URLs
if len(test_rows) < 5:
    extra = master[master["has_url"] == True].iloc[:5]
    test_rows = pd.concat([test_rows, extra]).drop_duplicates("company_name").head(5)

print(f"Testing on {len(test_rows)} companies:\n")

career_results  = []
enrich_results  = []

for _, row in test_rows.iterrows():
    name = row["company_name"]
    url  = row["url"] if pd.notna(row.get("url")) else None
    sic  = row["sic_code"] if pd.notna(row.get("sic_code")) else None

    print(f"\n{'─'*60}")
    print(f"  {name}  |  {url}")
    print(f"{'─'*60}")

    # ── Careers scrape ────────────────────────────────────────────────────────
    homepage_text, homepage_soup = (None, None)
    careers_url, careers_text    = None, None

    if url:
        homepage_text, homepage_soup = fetch_html(url)
        time.sleep(0.5)

    if homepage_soup:
        links = find_careers_links(url, homepage_soup)
        print(f"  Careers link candidates: {links[:3]}")
        for lnk in links:
            ct = fetch_html(lnk)[0]
            time.sleep(0.4)
            if ct:
                careers_url, careers_text = lnk, ct
                break

    careers_gpt = gpt_careers(name, url, careers_url,
                               careers_text or homepage_text or "(no page text)")
    roles = careers_gpt.get("roles", [])
    print(f"  has_careers={careers_gpt.get('has_careers_page')}  "
          f"roles={len(roles)}  email={careers_gpt.get('contact_email')}")
    for r in roles[:3]:
        print(f"    • {r.get('title')} [{r.get('type')}] @ {r.get('location')}")

    career_results.append({
        "company_name"    : name,
        "company_url"     : url,
        "careers_url"     : careers_url,
        "has_careers_page": careers_gpt.get("has_careers_page"),
        "role_count"      : len(roles),
        "roles_json"      : json.dumps(roles),
        "contact_email"   : careers_gpt.get("contact_email"),
        "apply_url"       : careers_gpt.get("apply_url"),
        "summary"         : careers_gpt.get("summary"),
    })

    # ── Enrichment ────────────────────────────────────────────────────────────
    enrich_gpt = gpt_enrich(name, url, sic, homepage_text)
    print(f"  stage={enrich_gpt.get('stage')}  "
          f"tags={enrich_gpt.get('sector_tags')}  "
          f"employees={enrich_gpt.get('employee_est')}")
    print(f"  description: {(enrich_gpt.get('description') or '')[:120]}")

    enrich_results.append({
        "company_name" : name,
        "url"          : url,
        "description"  : enrich_gpt.get("description"),
        "sector_tags"  : json.dumps(enrich_gpt.get("sector_tags", [])),
        "stage"        : enrich_gpt.get("stage"),
        "tech_keywords": enrich_gpt.get("tech_keywords"),
        "employee_est" : enrich_gpt.get("employee_est"),
        "hiring_status": enrich_gpt.get("hiring_status"),
        "founded_year" : enrich_gpt.get("founded_year"),
    })

# Save test outputs
pd.DataFrame(career_results).to_csv(
    BASE / "pipeline" / "output" / "test_careers.csv", index=False)
pd.DataFrame(enrich_results).to_csv(
    BASE / "pipeline" / "output" / "test_enriched.csv", index=False)

print(f"\n\n{'='*60}")
print("TEST COMPLETE — outputs saved to pipeline/output/test_*.csv")
print("Review above and in the CSVs, then run the full pipeline if happy.")
print(f"{'='*60}")
