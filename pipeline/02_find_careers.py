"""
Script 02: Careers page finder + role scraper.

For each company with a URL in master_companies.csv:
  1. Fetch homepage → find careers/jobs page links
  2. Fetch careers page
  3. Ask GPT-4o-mini to extract: open roles, contact email, apply URL

Saves results incrementally to pipeline/output/careers.csv so progress
is preserved if you interrupt and re-run (already-done companies are skipped).

Estimated cost: ~$0.15–0.25 for all ~432 hub companies.

Run with:
    python 02_find_careers.py
    (requires: pip install openai requests beautifulsoup4)
"""

import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent.parent
MASTER_CSV = BASE / "pipeline" / "output" / "master_companies.csv"
OUT_CSV    = BASE / "pipeline" / "output" / "careers.csv"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # export OPENAI_API_KEY=sk-...
MODEL          = "gpt-4o-mini"

FETCH_TIMEOUT  = 12    # seconds per HTTP request
REQUEST_DELAY  = 0.5   # seconds between requests (polite crawling)
MAX_PAGE_CHARS = 12000 # truncate page text fed to GPT (keeps token cost down)

# Keywords that strongly suggest a careers/jobs page
CAREERS_KEYWORDS = re.compile(
    r'\b(careers?|jobs?|vacancies|vacanci|openings?|hiring|join us|'
    r'work with us|join the team|opportunities)\b',
    re.IGNORECASE
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Clients ───────────────────────────────────────────────────────────────────
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch(url: str, timeout: int = FETCH_TIMEOUT) -> str | None:
    """GET a URL, return plain text or None on failure."""
    try:
        resp = requests.get(url, timeout=timeout, headers=HEADERS,
                            allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        # Remove nav/footer/script noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        return None


def fetch_html(url: str, timeout: int = FETCH_TIMEOUT):
    """Return (text, soup) or (None, None)."""
    try:
        resp = requests.get(url, timeout=timeout, headers=HEADERS,
                            allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text, soup
    except Exception:
        return None, None


def find_careers_links(base_url: str, soup) -> list[str]:
    """Extract absolute URLs of links that look like careers pages."""
    from urllib.parse import urljoin, urlparse
    base_domain = urlparse(base_url).netloc

    candidates = []
    for a in soup.find_all("a", href=True):
        href  = a["href"].strip()
        text  = a.get_text(strip=True)
        label = f"{href} {text}"
        if CAREERS_KEYWORDS.search(label):
            full = urljoin(base_url, href)
            # Keep only same-domain links (avoids LinkedIn job boards etc.)
            if urlparse(full).netloc == base_domain and full not in candidates:
                candidates.append(full)

    # Deduplicate, put shorter (more root-level) URLs first
    candidates.sort(key=len)
    return candidates[:5]   # top 5 candidates


def ask_gpt(company_name: str, company_url: str,
            careers_url: str | None, page_text: str) -> dict:
    """
    Ask GPT-4o-mini to extract structured careers info from page text.
    Returns a dict with keys: has_careers_page, roles, contact_email,
    apply_url, summary, raw_model.
    """
    source_label = careers_url if careers_url else company_url

    prompt = f"""You are analysing a company's website to find job opportunities.
Company: {company_name}
Page URL: {source_label}

Page text (truncated):
---
{page_text[:MAX_PAGE_CHARS]}
---

Extract the following as a JSON object (use null for missing fields):
{{
  "has_careers_page": true/false,     // Does this page contain job/careers info?
  "roles": [                          // List of open roles found (empty list if none)
    {{"title": "...", "type": "full-time/part-time/contract/unknown",
      "location": "...", "url": "..."}}
  ],
  "contact_email": "...",            // Email address for job applications (or null)
  "apply_url": "...",                // Direct URL to apply/ATS (or null)
  "summary": "..."                   // 1-sentence summary of what jobs are available
}}
Return ONLY the JSON object, no other text."""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        data["raw_model"] = MODEL
        return data
    except Exception as e:
        return {"error": str(e), "raw_model": MODEL}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    master = pd.read_csv(MASTER_CSV)
    companies_with_url = master[master["has_url"] == True].copy()
    print(f"Companies with URLs to process: {len(companies_with_url)}")

    # Load existing results (for incremental resumption)
    if OUT_CSV.exists():
        done = set(pd.read_csv(OUT_CSV)["company_name"].tolist())
        print(f"Already processed: {len(done)} (will skip these)")
    else:
        done = set()

    todo = companies_with_url[
        ~companies_with_url["company_name"].isin(done)
    ]
    print(f"Remaining to process: {len(todo)}\n")

    results = []
    errors  = []

    for i, (_, row) in enumerate(todo.iterrows(), 1):
        name = row["company_name"]
        url  = row["url"]

        if not isinstance(url, str) or not url.startswith("http"):
            url = f"https://{url}" if isinstance(url, str) else None

        if not url:
            continue

        print(f"[{i:3d}/{len(todo)}] {name[:45]:<45} {url[:50]}")

        # Step 1: Fetch homepage
        homepage_text, homepage_soup = fetch_html(url)
        time.sleep(REQUEST_DELAY)

        if not homepage_text:
            print(f"            ✗ homepage unreachable")
            results.append({
                "company_name"  : name,
                "company_url"   : url,
                "careers_url"   : None,
                "has_careers_page": False,
                "roles_json"    : "[]",
                "contact_email" : None,
                "apply_url"     : None,
                "summary"       : "Could not reach website",
                "scrape_status" : "homepage_error",
            })
            continue

        # Step 2: Look for careers page link
        careers_links = find_careers_links(url, homepage_soup)
        careers_text  = None
        careers_url   = None

        if careers_links:
            for cl in careers_links:
                ct = fetch(cl)
                time.sleep(REQUEST_DELAY)
                if ct:
                    careers_url  = cl
                    careers_text = ct
                    print(f"            ✓ careers page: {cl[:60]}")
                    break

        # Step 3: decide what text to send to GPT
        if careers_text:
            gpt_text     = careers_text
            scrape_status = "careers_page_found"
        else:
            # Fallback: use homepage text + note that we looked
            gpt_text     = homepage_text
            scrape_status = "homepage_only"
            if careers_links:
                print(f"            ~ careers links found but couldn't fetch")
            else:
                print(f"            ~ no careers links found, using homepage")

        # Step 4: GPT extraction
        gpt_result = ask_gpt(name, url, careers_url, gpt_text)

        roles = gpt_result.get("roles", [])
        print(f"            → {len(roles)} roles | "
              f"email: {gpt_result.get('contact_email') or '—'} | "
              f"has_careers: {gpt_result.get('has_careers_page')}")

        results.append({
            "company_name"    : name,
            "company_url"     : url,
            "careers_url"     : careers_url,
            "has_careers_page": gpt_result.get("has_careers_page", False),
            "roles_json"      : json.dumps(gpt_result.get("roles", [])),
            "role_count"      : len(roles),
            "contact_email"   : gpt_result.get("contact_email"),
            "apply_url"       : gpt_result.get("apply_url"),
            "summary"         : gpt_result.get("summary"),
            "scrape_status"   : scrape_status,
        })

        # Incremental save every 10 companies
        if i % 10 == 0:
            _append_save(results, OUT_CSV, done)
            results = []
            print(f"  ── checkpoint saved ({i} processed) ──\n")

    # Final save
    _append_save(results, OUT_CSV, done)

    # Summary
    final = pd.read_csv(OUT_CSV)
    print(f"\n{'='*55}")
    print(f"  CAREERS SCRAPE SUMMARY")
    print(f"{'='*55}")
    print(f"  Total processed    : {len(final)}")
    print(f"  Has careers page   : {final['has_careers_page'].sum()}")
    print(f"  Has contact email  : {final['contact_email'].notna().sum()}")
    print(f"  Total roles found  : {final['role_count'].sum()}")
    print(f"  Homepage errors    : {(final['scrape_status']=='homepage_error').sum()}")
    print(f"{'='*55}")
    print(f"\n✓ Saved → {OUT_CSV.relative_to(BASE)}")


def _append_save(new_rows: list, path: Path, already_done: set):
    """Append new rows to the output CSV."""
    if not new_rows:
        return
    df = pd.DataFrame(new_rows)
    if path.exists():
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, index=False)
    already_done.update(df["company_name"].tolist())


if __name__ == "__main__":
    main()
