"""
Script 01: Merge hub companies with Companies House data + validate.

Strategy:
- Loads hub companies (scraped_companies.csv) → 432 companies with URLs
- Loads CH data (companies_house_cambridge_tech.csv) → 326 CH companies
- Matches on company name using token-based Jaccard similarity
  (better than character fuzzy for company names because it avoids matching
  on shared generic suffixes like "Therapeutics", "Technologies" etc.)
- Produces pipeline/output/master_companies.csv with combined data
  + validation status

Run with:
    python 01_merge_validate.py
    (works in hspy1 conda env or VM Python — no extra dependencies needed)
"""

import pandas as pd
import re
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).parent.parent          # Cambridge job site/
HUB_CSV   = BASE / "scraped_companies.csv"
CH_CSV    = BASE / "companies_house_cambridge_tech.csv"
OUT_CSV   = BASE / "pipeline" / "output" / "master_companies.csv"
MATCH_CSV = BASE / "pipeline" / "output" / "match_report.csv"

# ── Config ───────────────────────────────────────────────────────────────────
# Jaccard threshold (0-1). 0.5 means ≥50% of distinctive tokens must overlap.
JACCARD_THRESHOLD = 0.50

# Legal suffixes to strip before comparison — keep domain terms (therapeutics,
# technologies etc.) since they ARE distinctive between companies.
_LEGAL_STRIP = re.compile(
    r'\b(limited|ltd|plc|llp|lp|the|uk|inc|co|corp|group|holdings|'
    r'international|worldwide)\b',
    re.IGNORECASE
)

# Allow single-char tokens — they're meaningful in company names like
# "T-Therapeutics", "CN-Bio", "F-Star" etc. Filtering them out causes false
# positives when two companies share only generic suffixes (e.g. "Therapeutics").
_MIN_TOKEN_LEN = 1


# ── Helpers ──────────────────────────────────────────────────────────────────
def tokenise(name: str) -> frozenset[str]:
    """Lowercase, strip legal suffixes, split into word tokens."""
    if not isinstance(name, str) or not name.strip():
        return frozenset()
    s = name.lower()
    s = _LEGAL_STRIP.sub(" ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)   # punctuation → space
    tokens = {t for t in s.split() if len(t) >= _MIN_TOKEN_LEN}
    return frozenset(tokens)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def best_match(hub_tok: frozenset,
               ch_tokens: list[frozenset]) -> tuple[int, float]:
    """Return (index_in_ch_tokens, jaccard_score) for the best match."""
    best_idx, best_sc = -1, 0.0
    for i, ch_tok in enumerate(ch_tokens):
        sc = jaccard(hub_tok, ch_tok)
        if sc > best_sc:
            best_sc, best_idx = sc, i
    return best_idx, best_sc


# ── Load data ────────────────────────────────────────────────────────────────
print("Loading data …")
hub = pd.read_csv(HUB_CSV)
ch  = pd.read_csv(CH_CSV)

print(f"  Hub companies : {len(hub)}")
print(f"  CH  companies : {len(ch)}")

ch["company_number"] = ch["company_number"].astype(str).str.strip()

# Pre-compute token sets
hub_tokens = [tokenise(n) for n in hub["company_name"]]
ch_tokens  = [tokenise(n) for n in ch["company_name"]]

# ── Matching ──────────────────────────────────────────────────────────────────
print(f"\nMatching (Jaccard threshold ≥ {JACCARD_THRESHOLD}) …")

match_results = []
for hub_idx, hub_tok in enumerate(hub_tokens):
    ch_idx, score = best_match(hub_tok, ch_tokens)
    matched = score >= JACCARD_THRESHOLD
    match_results.append({
        "hub_idx"      : hub_idx,
        "ch_idx"       : ch_idx if matched else -1,
        "score"        : round(score, 3),
        "matched"      : matched,
        "hub_name"     : hub.loc[hub_idx, "company_name"],
        "ch_name"      : ch.loc[ch_idx, "company_name"] if matched else "",
        "hub_tokens"   : " | ".join(sorted(hub_tok)),
        "ch_tokens"    : " | ".join(sorted(ch_tokens[ch_idx])) if matched else "",
    })

matches_df = pd.DataFrame(match_results)

# ── Sanity check: flag CH records matched by more than one hub entry ──────────
# (means duplicates in hub list, or a genuine ambiguity to review)
ch_idx_counts = (
    matches_df[matches_df["matched"]]
    .groupby("ch_idx")["hub_idx"]
    .count()
    .rename("n_hub_matches")
)
multi = ch_idx_counts[ch_idx_counts > 1]
if len(multi):
    print(f"\n  ⚠  {len(multi)} CH records matched by >1 hub entry (duplicates/ambiguities):")
    for ci, cnt in multi.items():
        rows = matches_df[(matches_df["ch_idx"] == ci) & matches_df["matched"]]
        print(f"     CH: {ch.loc[ci, 'company_name']!r:50s} ← hub: "
              + ", ".join(repr(r) for r in rows["hub_name"]))

n_matched = matches_df["matched"].sum()
print(f"\n  Matched  : {n_matched} hub companies linked to CH records")
print(f"  Unmatched: {len(hub) - n_matched} hub companies (no CH record found)")

# Save full match report
matches_df.to_csv(MATCH_CSV, index=False)
print(f"  → Match report saved to {MATCH_CSV.relative_to(BASE)}")

# ── Build master dataframe ────────────────────────────────────────────────────
print("\nBuilding master companies dataframe …")

records = []

# 1. Hub companies (with or without CH match)
for _, row in matches_df.iterrows():
    hub_row = hub.iloc[int(row["hub_idx"])]
    rec = {
        "company_name"  : hub_row["company_name"],
        "url"           : hub_row.get("url", ""),
        "source"        : "hub",
        "hub_name"      : hub_row.get("hub_name", ""),
        "hub_type"      : hub_row.get("hub_type", ""),
        # CH fields (filled if matched)
        "company_number": None,
        "postcode"      : None,
        "ch_status"     : None,
        "sic_code"      : None,
        "company_size"  : None,
        "incorporated"  : None,
        "last_accounts" : None,
        "address"       : None,
        "ch_validated"  : False,
        "ch_match_score": None,
        "ch_match_name" : None,
    }

    if row["matched"]:
        ch_row = ch.iloc[int(row["ch_idx"])]
        rec.update({
            "company_number": ch_row["company_number"],
            "postcode"      : ch_row.get("postcode"),
            "ch_status"     : ch_row.get("status"),
            "sic_code"      : ch_row.get("sic_code_1"),
            "company_size"  : ch_row.get("company_size"),
            "incorporated"  : ch_row.get("incorporated"),
            "last_accounts" : ch_row.get("last_accounts"),
            "address"       : ch_row.get("address"),
            "ch_validated"  : True,
            "ch_match_score": row["score"],
            "ch_match_name" : row["ch_name"],
        })

    records.append(rec)

# 2. CH-only companies (not matched to any hub entry) → keep for completeness
matched_ch_indices = set(
    matches_df.loc[matches_df["matched"], "ch_idx"].astype(int).tolist()
)
ch_only_count = 0
for ch_idx, ch_row in ch.iterrows():
    if ch_idx not in matched_ch_indices:
        records.append({
            "company_name"  : ch_row["company_name"],
            "url"           : None,
            "source"        : "companies_house",
            "hub_name"      : None,
            "hub_type"      : None,
            "company_number": ch_row["company_number"],
            "postcode"      : ch_row.get("postcode"),
            "ch_status"     : ch_row.get("status"),
            "sic_code"      : ch_row.get("sic_code_1"),
            "company_size"  : ch_row.get("company_size"),
            "incorporated"  : ch_row.get("incorporated"),
            "last_accounts" : ch_row.get("last_accounts"),
            "address"       : ch_row.get("address"),
            "ch_validated"  : True,
            "ch_match_score": None,
            "ch_match_name" : None,
        })
        ch_only_count += 1

master = pd.DataFrame(records)

# ── Derived columns ───────────────────────────────────────────────────────────
BAD_STATUSES = {"dissolved", "liquidation", "receivership", "administration",
                "voluntary arrangement", "insolvency proceedings"}
master["ch_concern"] = (
    master["ch_status"].fillna("").str.lower().isin(BAD_STATUSES)
)
master["has_url"] = master["url"].notna() & (master["url"].fillna("") != "")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print("  MASTER DATAFRAME SUMMARY")
print(f"{'='*55}")
print(f"  Total companies         : {len(master)}")
print(f"  Hub (with URLs)         : {(master['source']=='hub').sum()}")
print(f"  CH-only (no URL yet)    : {(master['source']=='companies_house').sum()}")
print(f"  Hub + CH validated      : {(master['ch_validated'] & (master['source']=='hub')).sum()}")
print(f"  Hub only (no CH match)  : {(~master['ch_validated'] & (master['source']=='hub')).sum()}")
print(f"  Has URL                 : {master['has_url'].sum()}")
print(f"  CH status concerns      : {master['ch_concern'].sum()}")
print(f"{'='*55}")

# SIC breakdown for hub companies that got validated
print("\nTop SIC codes (hub companies matched to CH):")
matched_sic = master[master["ch_validated"] & (master["source"] == "hub")]["sic_code"]
print(matched_sic.value_counts().head(12).to_string())

# ── Save ──────────────────────────────────────────────────────────────────────
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
master.to_csv(OUT_CSV, index=False)
print(f"\n✓ Saved → {OUT_CSV.relative_to(BASE)}")
print(f"  {len(master)} rows × {len(master.columns)} columns")

# ── Spot-check confirmed matches ─────────────────────────────────────────────
conf = matches_df[matches_df["matched"]].sort_values("score", ascending=False)
print(f"\n=== CONFIRMED MATCHES (top 40, sorted by score) ===")
print(conf[["hub_name", "ch_name", "score"]].head(40).to_string(index=False))

# Near-misses for manual review
near = matches_df[(matches_df["score"] >= 0.40) & (~matches_df["matched"])].sort_values("score", ascending=False)
print(f"\n=== NEAR-MISSES (Jaccard 0.40–{JACCARD_THRESHOLD}, {len(near)} companies) ===")
print(near[["hub_name", "ch_name", "score"]].head(25).to_string(index=False))
