import json, re, random, math
import pandas as pd
from pathlib import Path
from collections import Counter
from datetime import date

random.seed(42)
# BASE is the directory containing this script, so it works from any machine
BASE = Path(__file__).resolve().parent
df   = pd.read_csv(BASE / 'pipeline/output/final_companies.csv')

# ── Postcode → (lat, lng) lookup — real geocoded coordinates ─────────────────
def _load_geocodes():
    gc = {}
    for fname in ['geocodes_a.json', 'geocodes_b.json']:
        p = BASE / 'pipeline/output' / fname
        if p.exists():
            with open(p) as f:
                gc.update(json.load(f))
    return gc

GEOCODES = _load_geocodes()   # {postcode: {lat, lon}}  (some lon values may be null)

# Outward-code centroids used only as final fallback for companies with no full postcode.
# These are rough geographic centres for each CB postcode district.
# For precise pin placement run geocode_postcodes.py (requires internet) to populate geocodes_a.json.
OUTWARD_CENTRES = {
    'CB1':  (52.2020, 0.1300),  # Cambridge city centre / Hills Road / Mill Road
    'CB2':  (52.1980, 0.1200),  # Central / south Cambridge / Trumpington
    'CB3':  (52.2040, 0.0960),  # West Cambridge / Newnham / Grange Road
    'CB4':  (52.2280, 0.1310),  # North Cambridge / Science Park / Chesterton
    'CB5':  (52.2140, 0.1870),  # East Cambridge / Fen Ditton
    'CB21': (52.1020, 0.2220),  # Granta Park / Great Abington / Linton
    'CB22': (52.1340, 0.1860),  # Babraham / Great Shelford / Sawston
    'CB23': (52.1980, 0.0460),  # West / Comberton / Cambourne / Barton
    'CB24': (52.2880, 0.1130),  # North / Milton / Cottenham / Longstanton
    'CB25': (52.2830, 0.2720),  # Northeast / Burwell / Swaffham Prior
}
CAM_CENTRE = (52.2054, 0.1132)

def postcode_latlon(pc):
    """
    Returns (lat, lon, is_real_geocode).
    is_real_geocode=True  → exact coords from geocodes_a/b.json
    is_real_geocode=False → outward-code centroid estimate or no coords at all
    Run geocode_postcodes.py from your machine to populate exact coords.
    """
    if not isinstance(pc, str) or not pc.strip():
        return None, None, False
    pc_norm = pc.strip().upper()
    # 1) Real geocoded lookup
    entry = GEOCODES.get(pc_norm)
    if entry and entry.get('lat') is not None and entry.get('lon') is not None:
        return entry['lat'], entry['lon'], True
    # 2) Outward-code centroid fallback (approximate)
    outer = pc_norm.split()[0]
    if outer in OUTWARD_CENTRES:
        lat, lon = OUTWARD_CENTRES[outer]
        return round(lat + random.gauss(0, 0.003), 5), \
               round(lon + random.gauss(0, 0.004), 5), False
    return None, None, False

print(f"Geocodes loaded: {len(GEOCODES)} postcodes ({sum(1 for v in GEOCODES.values() if v.get('lat') is not None)} with real coords)")

# ── Clean & prepare data ──────────────────────────────────────────────────────
def parse_tags(t):
    if pd.isna(t): return []
    try: return json.loads(t)
    except: return [str(t)] if t else []

def parse_roles(r):
    if pd.isna(r): return []
    try:
        roles = json.loads(r)
        return roles if isinstance(roles, list) else []
    except: return []

df['has_url']          = df['has_url'].fillna(False).astype(bool)
df['ch_validated']     = df['ch_validated'].fillna(False).astype(bool)
df['has_careers_page'] = df['has_careers_page'].fillna(False)
df['has_careers_page'] = df['has_careers_page'].astype(str).str.lower().isin(['true','1'])
df['role_count']       = df['role_count'].fillna(0).astype(int)
df['description']      = df['description'].fillna('')
df['stage']            = df['stage'].fillna('unknown')
df['hiring_status']    = df['hiring_status'].fillna('no_info')
df['employee_est']     = df['employee_est'].fillna('unknown')
df['tech_keywords']    = df['tech_keywords'].fillna('')
if 'careers_summary' not in df.columns:
    df['careers_summary'] = ''
df['careers_summary']  = df['careers_summary'].fillna('')
df['tags_list']        = df['sector_tags'].apply(parse_tags)
df['roles_list']       = df['roles_json'].apply(parse_roles)

# Build JS records
companies, roles_list = [], []
for _, r in df.iterrows():
    lat, lon, is_real = postcode_latlon(r.get('postcode'))
    if lat is None:      # no postcode: scatter loosely around Cambridge centre
        lat = round(CAM_CENTRE[0] + random.gauss(0, 0.006), 5)
        lon = round(CAM_CENTRE[1] + random.gauss(0, 0.007), 5)
        loc_approx = True
    else:
        # loc_approx=True for both no-postcode scatter AND outward-code estimates
        # (only False when we have a real geocode from geocodes_a/b.json)
        loc_approx = not is_real

    rec = dict(
        name       = r['company_name'],
        url        = str(r['url']) if pd.notna(r.get('url')) else '',
        source     = r.get('source',''),
        hub        = str(r['hub_name']) if pd.notna(r.get('hub_name')) else '',
        desc       = r['description'][:280] if r['description'] else '',
        tags       = r['tags_list'],
        tags_str   = ', '.join(r['tags_list']),
        stage      = r['stage'],
        employees  = r['employee_est'].replace('unknown','?'),
        hiring     = r['hiring_status'],
        ch         = bool(r['ch_validated']),
        postcode   = str(r['postcode']) if pd.notna(r.get('postcode')) else '',
        sic        = str(r['sic_code']) if pd.notna(r.get('sic_code')) else '',
        founded    = int(r['founded_year']) if pd.notna(r.get('founded_year')) else None,
        careers_url= str(r['careers_url']) if pd.notna(r.get('careers_url')) and str(r.get('careers_url')) not in ('nan','') else '',
        has_careers= bool(r['has_careers_page']),
        roles      = r['roles_list'],
        contact    = str(r['contact_email']) if pd.notna(r.get('contact_email')) else '',
        tech       = r['tech_keywords'],
        lat        = lat, lon = lon, loc_approx = loc_approx,
    )
    companies.append(rec)

    # Flatten roles for jobs tab
    for role in r['roles_list']:
        roles_list.append(dict(
            company    = r['company_name'],
            url        = rec['url'],
            careers_url= rec['careers_url'],
            tags       = rec['tags'],
            stage      = rec['stage'],
            title      = role.get('title',''),
            type_      = role.get('type','unknown'),
            location   = role.get('location','Cambridge'),
        ))

# Stats
all_tags     = [t for c in companies for t in c['tags']]
tag_counts   = Counter(all_tags).most_common(14)
stage_counts = Counter(c['stage'] for c in companies)
hire_counts  = Counter(c['hiring'] for c in companies)
all_sectors  = sorted(set(all_tags))
LAST_UPDATED = date.today().strftime('%-d %B %Y')

# Chart data
tag_labels = [t[0] for t in tag_counts]
tag_vals   = [t[1] for t in tag_counts]
stage_ord  = ['startup','scaleup','established','unknown']
stage_vals = [stage_counts.get(s,0) for s in stage_ord]
hire_keys  = ['actively_hiring','possibly_hiring','no_info']
hire_vals  = [hire_counts.get(k,0) for k in hire_keys]
emp_ord    = ['1-10','11-50','51-200','200-1000','1000+','unknown']
emp_counts = Counter(c['employees'] for c in companies)
emp_vals   = [emp_counts.get(e,0) for e in emp_ord]

sector_opts = '\n'.join(f'<option value="{s}">{s}</option>' for s in all_sectors)

# ── Table rows HTML ───────────────────────────────────────────────────────────
SECTOR_COLS = {
    'biotech':'#2d6a4f','pharma':'#1b4332','medtech':'#40916c',
    'diagnostics':'#52b788','genomics':'#74c69d','drug discovery':'#095d40',
    'AI/ML':'#023e8a','deep learning':'#0077b6','computer vision':'#0096c7',
    'NLP':'#00b4d8','data analytics':'#48cae4',
    'SaaS':'#7b2d8b','developer tools':'#9b59b6','software':'#6c3483',
    'hardware':'#d4380d','semiconductors':'#fa541c','photonics':'#ff7a45',
    'robotics':'#e67e22','IoT':'#f39c12',
    'quantum computing':'#1a1a2e','space':'#16213e','defence':'#0f3460',
    'cleantech':'#2e7d32','climate':'#388e3c','agritech':'#558b2f',
    'foodtech':'#689f38','healthtech':'#00695c','fintech':'#1565c0',
    'edtech':'#6a1b9a','cybersecurity':'#b71c1c',
    'consulting':'#37474f','research':'#455a64',
}
def sector_badge(tag):
    col = SECTOR_COLS.get(tag,'#607d8b')
    return f'<span class="badge" style="background:{col}">{tag}</span>'

rows_html = []
for c in companies:
    name_cell = f'<a href="{c["url"]}" target="_blank" class="co-link">{c["name"]}</a>' if c['url'] else c['name']
    tags_html = ' '.join(sector_badge(t) for t in c['tags'][:3])
    stage_cls = {'startup':'info','scaleup':'primary','established':'dark','unknown':'secondary'}.get(c['stage'],'secondary')
    hire_cls  = {'actively_hiring':'success','possibly_hiring':'warning','no_info':'secondary'}.get(c['hiring'],'secondary')
    hire_lbl  = {'actively_hiring':'Hiring','possibly_hiring':'Possibly','no_info':'?'}.get(c['hiring'],'?')
    jobs_lnk  = f'<a href="{c["careers_url"]}" target="_blank" class="btn btn-xs btn-outline-success">Jobs↗</a>' if c['careers_url'] else ''
    src_lbl   = 'Hub' if c['source']=='hub' else 'CH'
    src_cls   = 'primary' if c['source']=='hub' else 'secondary'
    rows_html.append(
        f'<tr data-tags="{c["tags_str"]}" data-stage="{c["stage"]}" '
        f'data-hiring="{c["hiring"]}" data-source="{c["source"]}">'
        f'<td>{name_cell}'
        f'<br><small class="text-muted">{c["desc"][:100]}{"…" if len(c["desc"])>100 else ""}</small></td>'
        f'<td class="nowrap">{tags_html}</td>'
        f'<td><span class="badge bg-{stage_cls}">{c["stage"]}</span></td>'
        f'<td class="text-center small">{c["employees"]}</td>'
        f'<td class="text-center"><span class="badge bg-{hire_cls}">{hire_lbl}</span></td>'
        f'<td class="text-center">{jobs_lnk}</td>'
        f'<td class="text-center">{"✓" if c["ch"] else ""}</td>'
        f'<td class="text-center"><span class="badge bg-{src_cls} opacity-75">{src_lbl}</span></td>'
        f'</tr>'
    )
table_rows = '\n'.join(rows_html)

# ── Write out JSON for JS embedding ──────────────────────────────────────────
co_json    = json.dumps(companies, ensure_ascii=False)
roles_json = json.dumps(roles_list, ensure_ascii=False)
stats_json = json.dumps(dict(
    total=len(companies), hiring=hire_counts.get('actively_hiring',0),
    startups=stage_counts.get('startup',0), scaleups=stage_counts.get('scaleup',0),
    ch_verified=sum(1 for c in companies if c['ch']),
    sectors=len(all_sectors), roles=len(roles_list),
    tag_labels=tag_labels, tag_vals=tag_vals,
    stage_vals=stage_vals, hire_vals=hire_vals,
    emp_vals=emp_vals,
))

print(f'Companies: {len(companies)}, Roles: {len(roles_list)}')
print(f'Sector options: {len(all_sectors)}')
print('Data ready.')

# Save intermediate JSON for use in next script (same directory as this script)
SITE_DATA_PATH = BASE / 'site_data.json'
with open(SITE_DATA_PATH,'w') as f:
    json.dump(dict(companies=companies, roles=roles_list,
                   sector_opts=sector_opts, table_rows=table_rows,
                   stats_json=stats_json, co_json=co_json,
                   roles_json=roles_json, last_updated=LAST_UPDATED), f)
print(f'Saved {SITE_DATA_PATH}')
