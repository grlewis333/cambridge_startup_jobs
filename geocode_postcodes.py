"""
geocode_postcodes.py
--------------------
Fetches real lat/lon for every postcode in final_companies.csv using postcodes.io,
and saves results to pipeline/output/geocodes_a.json.

Run this from your local machine (requires internet access):
    python3 geocode_postcodes.py

After it completes, rebuild the site:
    python3 build_site.py && python3 gen_html.py
"""

import json
import time
import httpx
import pandas as pd
from pathlib import Path

BASE        = Path(__file__).resolve().parent
MASTER_CSV  = BASE / "pipeline/output/final_companies.csv"
GEOCODES_A  = BASE / "pipeline/output/geocodes_a.json"


def geocode_uk_postcodes(pcs: list[str]) -> list[dict]:
    """
    Batch-geocode UK postcodes using postcodes.io.
    Returns a list of {clean_pc, lat, lon} dicts for successful lookups.
    Identical to the function used in the original pipeline.
    """
    url = "https://api.postcodes.io/postcodes"
    results = []
    for i in range(0, len(pcs), 100):
        batch = [p for p in pcs[i : i + 100] if p]
        try:
            r = httpx.post(url, json={"postcodes": batch}, timeout=20.0)
            if r.status_code == 200:
                for item in r.json()["result"]:
                    if item["result"]:
                        results.append({
                            "clean_pc": item["query"],
                            "lat":      item["result"]["latitude"],
                            "lon":      item["result"]["longitude"],
                        })
                    else:
                        print(f"  No result for: {item['query']}")
            else:
                print(f"  HTTP {r.status_code} on batch starting at index {i}")
        except Exception as e:
            print(f"  Error on batch {i}: {e}")
        time.sleep(0.1)   # be polite to the free API
    return results


def main():
    # Load master CSV
    df = pd.read_csv(MASTER_CSV)
    all_postcodes = (
        df["postcode"]
        .dropna()
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )
    print(f"Total unique postcodes in master CSV: {len(all_postcodes)}")

    # Load existing geocodes (so we don't re-fetch ones we already have)
    existing: dict = {}
    if GEOCODES_A.exists():
        existing = json.load(open(GEOCODES_A))
    already_done = {pc for pc, v in existing.items() if v.get("lat") is not None}
    print(f"Already geocoded: {len(already_done)}")

    to_fetch = [pc for pc in all_postcodes if pc not in already_done]
    print(f"Fetching {len(to_fetch)} new postcodes from postcodes.io...\n")

    if not to_fetch:
        print("Nothing to do — all postcodes already geocoded.")
        return

    results = geocode_uk_postcodes(to_fetch)

    # Update the geocodes dict
    fetched = 0
    for r in results:
        existing[r["clean_pc"]] = {"lat": r["lat"], "lon": r["lon"]}
        fetched += 1

    # Save back
    with open(GEOCODES_A, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"\nSuccessfully geocoded: {fetched}/{len(to_fetch)}")
    failed = [pc for pc in to_fetch if pc not in {r["clean_pc"] for r in results}]
    if failed:
        print(f"Failed / no result:    {failed}")
    print(f"\nSaved to {GEOCODES_A}")
    print("\nNow run:  python3 build_site.py && python3 gen_html.py")


if __name__ == "__main__":
    main()
