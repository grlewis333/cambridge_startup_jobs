# Cambridge Tech Job Board — Pipeline

## Setup

```bash
conda activate hspy1
pip install -r pipeline/requirements.txt
```

## Scripts (run in order from the `Cambridge job site/` directory)

### 1. Merge + validate  *(no network needed)*
Merges hub companies with Companies House data, fuzzy-matches on company names,
adds CH validation status and SIC codes.

```bash
python pipeline/01_merge_validate.py
```
Output: `pipeline/output/master_companies.csv`  (700 rows × 18 cols)
Also: `pipeline/output/match_report.csv` (full match diagnostics)

---

### 2. Careers page finder  *(requires network + OpenAI key)*
For each of the 432 hub companies with URLs:
- Fetches homepage, finds careers/jobs page links
- Scrapes careers page text
- Uses GPT-4o-mini to extract open roles, contact email, apply URL

Runs incrementally — safe to interrupt and re-run (skips already-done companies).
Estimated cost: ~$0.15–0.25.

```bash
python pipeline/02_find_careers.py
```
Output: `pipeline/output/careers.csv`

---

### 3. Company enrichment  *(requires network + OpenAI key)*
For every company in master_companies.csv:
- Fetches homepage (for URL-bearing companies)
- Uses GPT-4o-mini to generate: description, sector tags, stage, tech keywords,
  employee estimate, hiring status

Runs incrementally — safe to interrupt and re-run.
Estimated cost: ~$0.25–0.35.

*Best to run after Script 02* — it uses the careers summaries as extra context.

```bash
python pipeline/03_enrich_companies.py
```
Output: `pipeline/output/enriched_companies.csv`

---

## Output files

| File | Contents |
|------|----------|
| `master_companies.csv` | 700 companies, source, URL, CH validation, SIC code |
| `careers.csv` | Careers page URL, open roles (JSON), contact email per company |
| `enriched_companies.csv` | Description, sector tags, stage, tech keywords per company |
| `match_report.csv` | Full Jaccard matching diagnostics (hub ↔ CH) |

## Notes
- The OpenAI API key is already set in scripts 02/03 (from your notebook)
- Rate limiting: scripts add 0.4–0.5s delay between HTTP requests
- Checkpoints: scripts save every 10–25 companies, so interrupting is safe
- The CH filter (Cambridge postcodes, active, tech SIC codes) means all 268
  CH-only companies are already validated as active Cambridge tech firms
