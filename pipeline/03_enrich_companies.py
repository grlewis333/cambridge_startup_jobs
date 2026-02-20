"""
Script 03: GPT-based company enrichment.

For each company in master_companies.csv, generates:
  - description       : 2-3 sentence summary of what the company does
  - sector_tags       : list of up to 4 sector labels (e.g. "biotech", "SaaS")
  - stage             : startup / scaleup / established / unknown
  - founded_est       : estimated founding year (from CH or website)
  - tech_keywords     : key technologies mentioned (e.g. "CRISPR, ML, quantum")
  - employee_est      : rough employee range estimate
  - hiring_status     : actively_hiring / possibly_hiring / no_info

Strategy:
  - For companies WITH a URL: fetch homepage text (cached from script 02 if run)
    + feed to GPT with company name / SIC code for context.
  - For companies WITHOUT a URL (CH-only): use just company name + SIC code
    + ask GPT to synthesise from its training knowledge.

Saves incrementally to pipeline/output/enriched_companies.csv.

Estimated cost at gpt-4o-mini pricing:
  ~700 companies × 1500 avg input tokens = 1.05M tokens ≈ $0.16 input
  ~700 × 300 output tokens = 210K ≈ $0.13 output
  Total: ~$0.29

Run with:
    python 03_enrich_companies.py
    (requires: pip install openai requests beautifulsoup4)
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent.parent
MASTER_CSV  = BASE / "pipeline" / "output" / "master_companies.csv"
CAREERS_CSV = BASE / "pipeline" / "output" / "careers.csv"   # optional, for context
OUT_CSV     = BASE / "pipeline" / "output" / "enriched_companies.csv"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # export OPENAI_API_KEY=sk-...
MODEL          = "gpt-4o-mini"

FETCH_TIMEOUT   = 10
MAX_PAGE_CHARS  = 8000    # chars fed to GPT from homepage
REQUEST_DELAY   = 0.4

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Standard sector tags to pick from (keeps categorisation consistent)
SECTOR_LIST = (
    "biotech | pharma | medtech | diagnostics | genomics | "
    "AI/ML | deep learning | computer vision | NLP | "
    "SaaS | developer tools | fintech | edtech | cleantech | climate | "
    "quantum computing | photonics | semiconductors | hardware | robotics | "
    "cybersecurity | data analytics | IoT | space | defence | "
    "agritech | foodtech | healthtech | drug discovery | "
    "software | consulting | research"
)

# ── Client ────────────────────────────────────────────────────────────────────
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()


# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_homepage_text(url: str) -> str | None:
    """Fetch a homepage and return clean plain text."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers=HEADERS,
                            allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return None


def build_prompt(name: str, url: str | None, sic: str | None,
                 incorporated: str | None, homepage_text: str | None,
                 careers_summary: str | None) -> str:

    context_parts = []
    if url:
        context_parts.append(f"Website: {url}")
    if sic:
        context_parts.append(f"Companies House SIC code: {sic}")
    if incorporated:
        context_parts.append(f"Incorporated: {incorporated}")
    if careers_summary:
        context_parts.append(f"Careers page summary: {careers_summary}")
    if homepage_text:
        context_parts.append(
            f"\nHomepage text (truncated):\n---\n"
            f"{homepage_text[:MAX_PAGE_CHARS]}\n---"
        )

    context = "\n".join(context_parts) if context_parts else "(no additional context)"

    return f"""You are building a Cambridge tech company database for a job board.
Company name: {name}

Available context:
{context}

Using the context above (and your own knowledge if context is sparse), return a JSON object:
{{
  "description": "2-3 sentence plain-English summary of what the company does and its main product/focus",
  "sector_tags": ["tag1", "tag2"],   // 1-4 tags from this list: {SECTOR_LIST}
  "stage": "startup|scaleup|established|unknown",
  "tech_keywords": "comma-separated list of key technologies (e.g. CRISPR, PyTorch, Kubernetes)",
  "employee_est": "1-10|11-50|51-200|200-1000|1000+|unknown",
  "hiring_status": "actively_hiring|possibly_hiring|no_info",
  "founded_year": 2015,   // integer or null
  "hq_city": "Cambridge"  // primary HQ city, or null if unclear
}}

Return ONLY the JSON object."""


def ask_gpt(prompt: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    master  = pd.read_csv(MASTER_CSV)
    print(f"Companies to enrich: {len(master)}")

    # Optional: load careers summaries for extra context
    careers_map = {}
    if CAREERS_CSV.exists():
        careers = pd.read_csv(CAREERS_CSV)
        careers_map = dict(zip(careers["company_name"],
                               careers["summary"].fillna("")))
        print(f"Careers context loaded for {len(careers_map)} companies")

    # Incremental resumption
    if OUT_CSV.exists():
        done = set(pd.read_csv(OUT_CSV)["company_name"].tolist())
        print(f"Already enriched: {len(done)} (skipping)")
    else:
        done = set()

    todo = master[~master["company_name"].isin(done)]
    print(f"Remaining: {len(todo)}\n")

    results = []

    for i, (_, row) in enumerate(todo.iterrows(), 1):
        name = row["company_name"]
        url  = row["url"] if pd.notna(row.get("url")) else None
        sic  = row["sic_code"] if pd.notna(row.get("sic_code")) else None
        inc  = row["incorporated"] if pd.notna(row.get("incorporated")) else None

        print(f"[{i:3d}/{len(todo)}] {name[:50]:<50}", end=" ")

        # Fetch homepage (only for companies with URLs)
        homepage_text = None
        if url:
            homepage_text = fetch_homepage_text(url)
            time.sleep(REQUEST_DELAY)
            status = "✓ fetched" if homepage_text else "✗ fetch failed"
        else:
            status = "— no url"

        careers_summary = careers_map.get(name)

        # Build prompt and call GPT
        prompt  = build_prompt(name, url, sic, inc, homepage_text, careers_summary)
        gpt_out = ask_gpt(prompt)

        print(f"| {status} | stage={gpt_out.get('stage','?'):<12} "
              f"| {', '.join(gpt_out.get('sector_tags', []))[:35]}")

        # Flatten into output row
        results.append({
            "company_name"  : name,
            "url"           : url,
            "source"        : row.get("source"),
            "company_number": row.get("company_number"),
            "postcode"      : row.get("postcode"),
            "sic_code"      : sic,
            "ch_validated"  : row.get("ch_validated"),
            "ch_status"     : row.get("ch_status"),
            "incorporated"  : inc,
            "address"       : row.get("address"),
            "hub_name"      : row.get("hub_name"),
            "hub_type"      : row.get("hub_type"),
            # GPT enriched fields
            "description"   : gpt_out.get("description"),
            "sector_tags"   : json.dumps(gpt_out.get("sector_tags", [])),
            "stage"         : gpt_out.get("stage"),
            "tech_keywords" : gpt_out.get("tech_keywords"),
            "employee_est"  : gpt_out.get("employee_est"),
            "hiring_status" : gpt_out.get("hiring_status"),
            "founded_year"  : gpt_out.get("founded_year"),
            "hq_city"       : gpt_out.get("hq_city"),
            "enrich_error"  : gpt_out.get("error"),
        })

        # Checkpoint every 25 companies
        if i % 25 == 0:
            _append_save(results, OUT_CSV, done)
            results = []
            print(f"  ── checkpoint ({i} done) ──\n")

    _append_save(results, OUT_CSV, done)

    # Summary
    final = pd.read_csv(OUT_CSV)
    print(f"\n{'='*55}")
    print(f"  ENRICHMENT SUMMARY")
    print(f"{'='*55}")
    print(f"  Total enriched     : {len(final)}")
    print(f"  With description   : {final['description'].notna().sum()}")
    print(f"  Stage breakdown    :")
    print(final["stage"].value_counts().to_string())
    print(f"  Top sector tags    :")
    import ast
    all_tags = []
    for t in final["sector_tags"].dropna():
        try:
            all_tags.extend(json.loads(t))
        except Exception:
            pass
    from collections import Counter
    print(pd.Series(Counter(all_tags)).sort_values(ascending=False).head(15).to_string())
    print(f"{'='*55}")
    print(f"\n✓ Saved → {OUT_CSV.relative_to(BASE)}")


def _append_save(new_rows: list, path: Path, already_done: set):
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
