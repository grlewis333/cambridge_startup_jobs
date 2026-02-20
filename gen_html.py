import json
from pathlib import Path

# Read site_data.json from same directory as this script
SCRIPT_DIR = Path(__file__).resolve().parent
with open(SCRIPT_DIR / 'site_data.json') as f:
    d = json.load(f)

sector_opts  = d['sector_opts']
table_rows   = d['table_rows']
stats_json   = d['stats_json']
co_json      = d['co_json']
roles_json   = d['roles_json']
last_updated = d['last_updated']

STAGE_COLOURS = {'startup':'#0077b6','scaleup':'#6a0dad','established':'#333333','unknown':'#888888'}

HUB_LINKS = [
    ("Cambridge Enterprise",                 "https://www.enterprise.cam.ac.uk/"),
    ("St John's Innovation Centre",          "https://www.stjohns.co.uk/"),
    ("Accelerate Cambridge (JBS)",           "https://www.jbs.cam.ac.uk/entrepreneurship/programmes/accelerate-cambridge/"),
    ("IdeaSpace",                            "https://www.ideaspace.cam.ac.uk/"),
    ("Babraham Research Campus",             "https://www.babraham.com/"),
    ("Allia Future Business Centre",         "https://futurebusinesscentre.co.uk/"),
    ("Eagle Labs Cambridge (Barclays)",      "https://labs.uk.barclays/locations/cambridge"),
    ("Cambridge Innovation Capital",         "https://www.cic.vc/"),
    ("Cambridge Science Park",               "https://www.cambridgesciencepark.co.uk/"),
    ("The Bradfield Centre",                 "https://www.bradfieldcentre.com/"),
    ("Wellcome Genome Campus",               "https://www.wellcomegenomecampus.org/"),
    ("Cambridge Social Ventures (JBS)",      "https://www.jbs.cam.ac.uk/centres/social-innovation/cambridge-social-ventures/"),
    ("EPOC",                                 "https://www.epoc.group.cam.ac.uk/"),
    ("IQ Capital",                           "https://www.iqcapital.vc/"),
    ("Start Codon",                          "https://startcodon.co/"),
    ("One Nucleus",                          "https://www.onenucleus.com/"),
    ("Cambridge Cleantech",                  "https://www.cambridgecleantech.org.uk/"),
    ("Gen2 Cambridge",                       "https://gentwo.co.uk/life-sciences/"),
    ("Accelerate@Babraham",                  "https://www.accelerateatbabraham.com/about/"),
    ("Granta Park",                          "https://www.grantapark.com/"),
    ("Chesterford Research Park",            "https://www.chesterfordresearchpark.com/"),
    ("Cambridge Research Park",              "https://www.cambridgeresearchpark.co.uk/"),
    ("Melbourn Science Park",                "https://www.mellournsp.com/"),
    ("Cambridge Biomedical Campus",          "https://cambridge-biomedical.com/"),
]

hub_links_html = '\n'.join(
    f'<li><a href="{url}" target="_blank" style="color:#1b3a6b">{name}</a></li>'
    for name, url in HUB_LINKS
)

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cambridge Tech: Job Board</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css">
<style>
:root {{
  --navy:#0d1b2a; --blue:#1b3a6b; --accent:#e63946;
  --green:#2d6a4f; --pill-r:4px; --card-r:12px;
}}
body {{ background:#f0f2f7; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:#1a1a2e; }}

/* ── hero ── */
.hero {{
  background:linear-gradient(140deg,var(--navy) 0%,#1b3a6b 60%,#2d4a8a 100%);
  color:#fff; padding:2rem 0 1.6rem;
  border-bottom:3px solid var(--accent);
}}
.hero h1 {{ font-size:1.9rem; font-weight:800; letter-spacing:-.03em; margin:0; }}
.hero-sub {{ opacity:.72; font-size:.9rem; margin:.4rem 0 1rem; line-height:1.4; }}
.hero-byline {{ font-size:.75rem; opacity:.55; margin-top:.6rem; }}
.hero-byline a {{ color:rgba(255,255,255,.7); text-decoration:underline; text-decoration-color:rgba(255,255,255,.3); }}
.hero-byline a:hover {{ color:#fff; }}

.stat-pill {{
  background:rgba(255,255,255,.12); border-radius:14px; border:1px solid rgba(255,255,255,.15);
  padding:.6rem 1.1rem; text-align:center; min-width:90px;
  transition: background .15s;
}}
.stat-pill:hover {{ background:rgba(255,255,255,.18); }}
.stat-num  {{ font-size:1.65rem; font-weight:800; line-height:1; }}
.stat-lbl  {{ font-size:.65rem; opacity:.75; text-transform:uppercase; letter-spacing:.08em; margin-top:.1rem; }}

/* ── sticky filter bar ── */
.filter-bar {{
  background:#fff; border-bottom:1px solid #e0e4ea; padding:.65rem 0;
  position:sticky; top:0; z-index:999; box-shadow:0 2px 14px rgba(0,0,0,.07);
}}
.filter-bar .form-select, .filter-bar .form-control {{ font-size:.85rem; border-color:#d0d6df; border-radius:8px; }}
.filter-bar select, .filter-bar input {{ height:34px; padding:.25rem .6rem; }}
.btn-reset {{
  border:1px solid #d0d6df; background:#fff; border-radius:8px;
  font-size:.83rem; height:34px; color:#555; cursor:pointer;
}}
.btn-reset:hover {{ background:#f0f2f5; }}
.btn-export {{
  background:var(--navy); color:#fff; border:none; border-radius:8px;
  font-size:.8rem; height:34px; padding:0 .85rem; cursor:pointer;
  white-space:nowrap; transition: background .15s;
}}
.btn-export:hover {{ background:var(--blue); }}

/* ── tabs ── */
.tab-wrapper {{ background:#fff; border-bottom:1px solid #e0e4ea; }}
.nav-tabs {{ border:none; padding:0 1rem; }}
.nav-tabs .nav-link {{
  border:none; border-bottom:3px solid transparent; color:#555; font-size:.9rem;
  font-weight:600; padding:.75rem 1.2rem; border-radius:0; transition: color .1s;
}}
.nav-tabs .nav-link.active {{ color:var(--navy); border-bottom-color:var(--accent); background:none; }}
.nav-tabs .nav-link:hover:not(.active) {{ color:var(--blue); border-bottom-color:#ddd; background:none; }}
.tab-content {{ padding:1.5rem 0; }}

/* ── section titles ── */
.sec-title {{
  font-size:1.08rem; font-weight:700; color:var(--navy);
  border-left:4px solid var(--accent); padding-left:.7rem; margin-bottom:.5rem;
}}
.sec-sub {{ font-size:.82rem; color:#888; margin-bottom:1rem; margin-top:.15rem; }}

/* ── hiring cards ── */
.hire-card {{
  border:1px solid #e4eef6; border-radius:var(--card-r); background:#fff;
  padding:1rem 1.1rem; height:100%;
  transition:box-shadow .15s, transform .1s;
}}
.hire-card:hover {{ box-shadow:0 6px 20px rgba(0,0,0,.10); transform:translateY(-1px); }}
.hire-card h6 {{ font-size:.9rem; font-weight:700; margin:0 0 .35rem; }}
.hire-card h6 a {{ color:var(--navy); text-decoration:none; }}
.hire-card h6 a:hover {{ color:var(--accent); }}
.hire-card .card-desc {{ font-size:.78rem; color:#666; line-height:1.45; }}
.role-chip {{
  display:inline-block; background:#e8f0fc; color:#1b3a6b;
  border-radius:5px; font-size:.7rem; padding:.15rem .45rem; margin:.1rem .1rem 0 0;
}}

/* ── jobs board ── */
.job-card {{
  background:#fff; border-radius:var(--card-r); border:1px solid #e4eaef;
  padding:1rem 1.2rem; margin-bottom:.6rem; display:flex;
  align-items:flex-start; gap:1rem;
  transition:box-shadow .15s;
}}
.job-card:hover {{ box-shadow:0 4px 14px rgba(0,0,0,.08); }}
.job-co    {{ font-size:.78rem; color:#888; }}
.job-title {{ font-size:.97rem; font-weight:700; color:var(--navy); }}
.job-meta  {{ font-size:.78rem; color:#666; margin-top:.2rem; }}

/* ── map ── */
#map {{ height:580px; border-radius:var(--card-r); box-shadow:0 2px 12px rgba(0,0,0,.1); }}
.map-legend {{
  background:#fff; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,.12);
  padding:.75rem 1rem; font-size:.8rem; line-height:1.8;
}}
.legend-dot {{
  display:inline-block; width:12px; height:12px; border-radius:50%;
  margin-right:.4rem; vertical-align:middle; border:1.5px solid rgba(255,255,255,.6);
}}
.leaflet-popup-content-wrapper {{ border-radius:10px; font-size:.84rem; max-width:290px; }}
.map-count {{
  background:var(--navy); color:#fff; border-radius:8px;
  padding:.3rem .9rem; font-size:.8rem; font-weight:600;
}}

/* ── table ── */
#coTable td {{ vertical-align:middle; font-size:.84rem; }}
#coTable th  {{ font-size:.8rem; color:#555; }}
.co-link     {{ color:var(--navy); font-weight:600; text-decoration:none; }}
.co-link:hover {{ color:var(--accent); }}
.badge       {{ font-size:.67rem; font-weight:500; border-radius:var(--pill-r); }}
.nowrap      {{ white-space:nowrap; }}
.btn-xs      {{ padding:.1rem .45rem; font-size:.74rem; border-radius:5px; }}

/* ── about ── */
.about-card  {{
  background:#fff; border-radius:var(--card-r); padding:1.5rem;
  box-shadow:0 2px 10px rgba(0,0,0,.06);
}}
.step-num {{
  background:var(--navy); color:#fff; border-radius:50%;
  width:28px; height:28px; display:inline-flex; align-items:center;
  justify-content:center; font-size:.8rem; font-weight:700; flex-shrink:0;
}}
.caveat-box {{
  background:#fff8e1; border-left:4px solid #f5a623;
  border-radius:0 6px 6px 0; padding:1rem 1.2rem; font-size:.87rem;
}}
.author-card {{
  background:linear-gradient(135deg,#f0f4ff,#e8f0fc);
  border:1px solid #c7d9f5; border-radius:var(--card-r);
  padding:1.2rem; margin-top:.75rem;
}}

/* ── chart cards ── */
.chart-card {{
  background:#fff; border-radius:var(--card-r);
  box-shadow:0 2px 10px rgba(0,0,0,.06); padding:1.1rem 1.3rem;
}}

/* ── count badge ── */
.count-badge {{
  background:#eef4ff; color:var(--blue); border-radius:20px;
  padding:.1rem .75rem; font-size:.8rem; font-weight:600; margin-left:.4rem;
}}

/* ── no-results ── */
.no-results {{ text-align:center; color:#aaa; padding:3rem 1rem; font-size:.95rem; }}

/* ── footer ── */
.site-footer {{
  background:var(--navy); color:rgba(255,255,255,.55);
  padding:1.6rem 0; font-size:.82rem; margin-top:2rem;
}}
.site-footer a {{ color:rgba(255,255,255,.65); text-decoration:none; }}
.site-footer a:hover {{ color:#fff; }}
.site-footer .divider {{ opacity:.3; margin:0 .6rem; }}
</style>
</head>
<body>

<!-- ═══════════════ HERO ═══════════════ -->
<div class="hero">
<div class="container">
  <div class="mb-1" style="font-size:.72rem;letter-spacing:.14em;opacity:.5;text-transform:uppercase">Cambridge · UK · Tech Jobs</div>
  <h1>Cambridge's hidden tech jobs 🔬</h1>
  <p class="hero-sub">
    Startups and scaleups scraping genomes, building quantum computers, growing meat in bioreactors,
    that sort of thing. Many don't post jobs in expensive places like LinkedIn. This site finds them anyway.
  </p>
  <div class="d-flex flex-wrap gap-2" id="heroStats"></div>
  <p class="hero-byline mt-2">
    Built by <a href="https://www.linkedin.com/in/georgelewis94/" target="_blank">George Lewis</a> ·
    a personal data pipeline project · last updated {last_updated}
  </p>
</div>
</div>

<!-- ═══════════════ FILTER BAR ═══════════════ -->
<div class="filter-bar">
<div class="container">
  <div class="row g-2 align-items-center">
    <div class="col-12 col-md-3">
      <input type="text" id="fSearch" class="form-control" placeholder="🔍  Search companies…">
    </div>
    <div class="col-6 col-md-2">
      <select id="fSector" class="form-select">
        <option value="">All sectors</option>
        {sector_opts}
      </select>
    </div>
    <div class="col-6 col-md-2">
      <select id="fStage" class="form-select">
        <option value="">All stages</option>
        <option>startup</option><option>scaleup</option><option>established</option>
      </select>
    </div>
    <div class="col-6 col-md-2">
      <select id="fHiring" class="form-select">
        <option value="">All hiring status</option>
        <option value="actively_hiring">Actively hiring</option>
        <option value="possibly_hiring">Possibly hiring</option>
        <option value="no_info">No info</option>
      </select>
    </div>
    <div class="col-6 col-md-1">
      <select id="fSource" class="form-select">
        <option value="">All sources</option>
        <option value="hub">Hub</option>
        <option value="companies_house">CH</option>
      </select>
    </div>
    <div class="col-12 col-md-2 d-flex gap-2 justify-content-end">
      <button class="btn-reset" onclick="resetFilters()">Reset</button>
      <button class="btn-export" onclick="downloadCompaniesCSV()" title="Download filtered companies as CSV">↓ CSV</button>
    </div>
  </div>
</div>
</div>

<!-- ═══════════════ TABS ═══════════════ -->
<div class="tab-wrapper">
<div class="container">
  <ul class="nav nav-tabs" id="mainTabs">
    <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#tab-companies">🏢 Companies</a></li>
    <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#tab-jobs">💼 Jobs</a></li>
    <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#tab-map">🗺️ Map</a></li>
    <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#tab-about">ℹ️ About</a></li>
  </ul>
</div>
</div>

<div class="tab-content">

<!-- ═══ TAB: COMPANIES ═══ -->
<div class="tab-pane fade show active" id="tab-companies">
<div class="container">

  <!-- Landscape charts -->
  <div class="mb-4">
    <div class="sec-title">📊 Ecosystem Snapshot</div>
    <div class="sec-sub">What does Cambridge tech actually look like? (AI-classified, so grain of salt.)</div>
    <div class="row g-3">
      <div class="col-md-6"><div class="chart-card"><h6 class="text-muted" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.06em">Top sectors</h6><canvas id="sectorChart" height="220"></canvas></div></div>
      <div class="col-md-3"><div class="chart-card"><h6 class="text-muted" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.06em">Company stage</h6><canvas id="stageChart" height="220"></canvas></div></div>
      <div class="col-md-3"><div class="chart-card"><h6 class="text-muted" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.06em">Team size</h6><canvas id="empChart" height="220"></canvas></div></div>
    </div>
  </div>

  <!-- Actively hiring cards -->
  <div class="mb-4">
    <div class="sec-title">🟢 Actively Hiring <span class="count-badge" id="hiringCount">0</span></div>
    <div class="sec-sub">Found by an automated pipeline scanning career pages. Always double-check, these things go stale.</div>
    <div class="row g-3" id="hiringCards"></div>
    <div class="no-results d-none" id="hiringNone">No actively hiring companies match the current filters.</div>
  </div>

  <!-- Full company table -->
  <div class="mb-4">
    <div class="sec-title">All Companies <span class="count-badge" id="tableCount">0</span></div>
    <div class="bg-white rounded-3 shadow-sm p-3">
      <table id="coTable" class="table table-hover table-sm" style="width:100%">
        <thead class="table-light">
          <tr>
            <th style="min-width:240px">Company</th>
            <th>Sectors</th>
            <th>Stage</th>
            <th class="text-center">Size</th>
            <th class="text-center">Hiring</th>
            <th class="text-center">Jobs</th>
            <th class="text-center" title="Companies House filing profile">CH</th>
            <th class="text-center">Src</th>
          </tr>
        </thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </div>

</div><!-- /container -->
</div><!-- /tab-companies -->

<!-- ═══ TAB: JOBS ═══ -->
<div class="tab-pane fade" id="tab-jobs">
<div class="container">

  <div class="d-flex align-items-center gap-3 mb-1">
    <div class="sec-title mb-0">💼 Open Roles <span class="count-badge" id="jobsCount">0</span></div>
    <button class="btn-export ms-auto" onclick="downloadRolesCSV()" title="Download roles as CSV">↓ CSV</button>
  </div>
  <div class="sec-sub">Roles actually found on careers pages. Coverage is partial, as lots of companies just don't post roles publicly.</div>
  <div class="mb-3" style="max-width:400px">
    <input type="text" id="jobSearch" class="form-control" placeholder="🔍  Search roles…">
  </div>
  <div id="jobsList"></div>
  <div class="no-results d-none" id="jobsNone">No matching roles found. Try casting a wider net with the filters above, or check the outreach section below.</div>

  <!-- Actively hiring without specific roles -->
  <div class="mt-4">
    <div class="sec-title" style="font-size:.95rem">📩 Actively Hiring: Worth a Cold Email <span class="count-badge" id="outreachCount">0</span></div>
    <div class="sec-sub">These companies look like they're hiring but didn't have specific roles listed publicly. A speculative email often works better anyway.</div>
    <div class="row g-3" id="outreachCards"></div>
  </div>

</div><!-- /container -->
</div><!-- /tab-jobs -->

<!-- ═══ TAB: MAP ═══ -->
<div class="tab-pane fade" id="tab-map">
<div class="container">

  <div class="row g-3 mb-3 align-items-start">
    <div class="col">
      <div class="sec-title mb-1">🗺️ Cambridge Tech Landscape</div>
      <div class="sec-sub mb-0">
        Pinned to registered postcode where available (CH data), otherwise scattered
        around the approximate Cambridge area. Green badge = actively hiring.
        Click numbered clusters to zoom in and see individual companies.
        <span class="map-count ms-2" id="mapCount">0 companies</span>
      </div>
      <div class="mt-2">
        <button id="btnDots"  onclick="setMapMode('dots')"  class="btn btn-sm btn-primary me-1">📍 Dots</button>
        <button id="btnHeat"  onclick="setMapMode('heat')"  class="btn btn-sm btn-outline-secondary">🌡️ Heatmap</button>
      </div>
    </div>
    <div class="col-auto">
      <div class="map-legend">
        <div><span class="legend-dot" style="background:#0077b6"></span>Startup</div>
        <div><span class="legend-dot" style="background:#6a0dad"></span>Scaleup</div>
        <div><span class="legend-dot" style="background:#333"></span>Established</div>
        <div><span class="legend-dot" style="background:#888"></span>Unknown</div>
        <hr class="my-1">
        <div style="opacity:.55;font-size:.7rem">⊕ approximate location</div>
      </div>
    </div>
  </div>
  <div id="map"></div>

</div><!-- /container -->
</div><!-- /tab-map -->

<!-- ═══ TAB: ABOUT ═══ -->
<div class="tab-pane fade" id="tab-about">
<div class="container">

  <div class="row g-4">
    <div class="col-lg-8">
      <div class="about-card mb-4">
        <h5 class="fw-bold mb-1">What is this?</h5>
        <p style="font-size:.9rem;color:#444">
          Cambridge has an unusually dense tech ecosystem: Nobel laureates spinning out biotech companies,
          ex-ARM engineers building quantum chips, that sort of thing. But most of these places don't post
          on LinkedIn, so they're basically invisible if you're job hunting the normal way.
        </p>
        <p style="font-size:.9rem;color:#444">
          This site is my attempt to map them out and surface the opportunities. I've built a pipeline that
          automatically scrapes and refreshes this data, so it can be kept up to date over time.
          Not affiliated with any of the hubs or companies listed.
        </p>

        <h6 class="fw-bold mt-3 mb-2">How it works</h6>
        <div class="d-flex gap-3 mb-2 align-items-start">
          <span class="step-num">1</span>
          <div style="font-size:.88rem"><strong>Hub scraping</strong>: the pipeline scrapes {len(HUB_LINKS)} Cambridge startup hubs and science parks to build a list of ~430 portfolio companies, each with a website.</div>
        </div>
        <div class="d-flex gap-3 mb-2 align-items-start">
          <span class="step-num">2</span>
          <div style="font-size:.88rem"><strong>Companies House bulk data</strong>: the full UK company register (5.6M rows, processed with Polars) is filtered to active Cambridge-postcode tech companies (SIC codes 62x, 63x, 72x, 21x, 26x, 71x), adding ~280 more.</div>
        </div>
        <div class="d-flex gap-3 mb-2 align-items-start">
          <span class="step-num">3</span>
          <div style="font-size:.88rem"><strong>Fuzzy merge</strong>: hub companies are matched against the CH register via token Jaccard similarity, which sounds fancier than it is but works well enough to link postcodes and verify active status.</div>
        </div>
        <div class="d-flex gap-3 mb-3 align-items-start">
          <span class="step-num">4</span>
          <div style="font-size:.88rem"><strong>AI enrichment</strong>: GPT-4o mini reads each company's homepage and generates a description, sector tags, stage estimate, and a hiring status guess. Careers pages are scraped where accessible.</div>
        </div>

        <div class="caveat-box">
          <strong>⚠️ Caveats: please read</strong><br>
          This is a personal side project and may be incomplete, out of date, or just wrong in places.
          Hiring status is inferred from website content at a point in time, so always verify directly.
          Sector tags and descriptions are AI-generated and occasionally confidently incorrect.
          <br><br>
          <strong>Last updated:</strong> {last_updated}
        </div>

        <div class="author-card">
          <div style="font-size:.9rem">
            <strong>Built by George Lewis</strong>,
            scientist, data nerd, occasional web scraper.
            <a href="https://www.linkedin.com/in/georgelewis94/" target="_blank" style="color:var(--blue)">LinkedIn ↗</a>
            &nbsp;·&nbsp;
            <a href="https://github.com/grlewis333/cambridge_startup_jobs" target="_blank" style="color:var(--blue)">GitHub ↗</a>
          </div>
          <div style="font-size:.8rem;color:#666;margin-top:.3rem">
            Spotted an error, want to add a company, or want me to refresh the data? Drop me a message on <a href="https://www.linkedin.com/in/georgelewis94/" target="_blank" style="color:var(--blue)">LinkedIn</a>.
          </div>
        </div>
      </div>
    </div>

    <div class="col-lg-4">
      <div class="about-card mb-3">
        <h6 class="fw-bold">Hubs &amp; parks scraped</h6>
        <ul class="mb-0" style="font-size:.84rem;padding-left:1.2rem;line-height:1.9">
          {hub_links_html}
        </ul>
      </div>
      <div class="about-card mb-3">
        <h6 class="fw-bold">Coverage</h6>
        <div style="font-size:.87rem;line-height:1.9">
          <div>700 companies total</div>
          <div>332 Companies House verified</div>
          <div>Cambridge postcodes CB1–CB25</div>
          <div>Sectors: software, biotech, hardware, AI/ML, cleantech &amp; more</div>
        </div>
      </div>
      <div class="about-card">
        <h6 class="fw-bold">Built with</h6>
        <p style="font-size:.85rem;margin:0;color:#555;line-height:1.7">
          Python (pandas, polars, BeautifulSoup), GPT-4o mini,
          Companies House bulk data, Leaflet.js, Chart.js,
          Bootstrap 5, DataTables.
        </p>
      </div>
    </div>
  </div>

</div><!-- /container -->
</div><!-- /tab-about -->

</div><!-- /tab-content -->

<!-- ═══════════════ FOOTER ═══════════════ -->
<footer class="site-footer">
<div class="container">
  <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
    <div>
      <span style="color:rgba(255,255,255,.8);font-weight:600">Cambridge Tech Job Board</span>
      <span class="divider">·</span>
      Built by <a href="https://www.linkedin.com/in/georgelewis94/" target="_blank">George Lewis</a>
      <span class="divider">·</span>
      <a href="https://github.com/grlewis333/cambridge_startup_jobs" target="_blank">GitHub ↗</a>
    </div>
    <div>
      Personal project, not affiliated with any listed company or hub.
      <span class="divider">·</span>
      Last updated: {last_updated}
    </div>
  </div>
</div>
</footer>

<!-- ═══════════════ SCRIPTS ═══════════════ -->
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.heat/0.2.0/leaflet-heat.js"></script>

<script>
const ALL = {co_json};
const ALL_ROLES = {roles_json};
const STATS = {stats_json};

// ── colour maps ──
const SCOL = {json.dumps(STAGE_COLOURS)};
const TCOL = {json.dumps({k: v for k, v in {
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
}.items()})};

function tagBadge(t) {{
  const col = TCOL[t] || '#607d8b';
  return `<span class="badge" style="background:${{col}}">${{t}}</span>`;
}}

// ── filter state ──
const state = {{search:'', sector:'', stage:'', hiring:'', source:''}};

function getFiltered() {{
  const s = state.search.toLowerCase();
  return ALL.filter(c => {{
    if (s && !c.name.toLowerCase().includes(s) && !c.desc.toLowerCase().includes(s) && !c.tags_str.toLowerCase().includes(s)) return false;
    if (state.sector && !c.tags.includes(state.sector)) return false;
    if (state.stage  && c.stage  !== state.stage)  return false;
    if (state.hiring && c.hiring !== state.hiring) return false;
    if (state.source && c.source !== state.source) return false;
    return true;
  }});
}}

// ── hero stats ──
function renderHero() {{
  const h = document.getElementById('heroStats');
  const pills = [
    [ALL.length, 'Companies'], [STATS.hiring, 'Actively Hiring'],
    [STATS.startups, 'Startups'], [STATS.scaleups, 'Scaleups'],
    [STATS.ch_verified, 'CH Verified'], [STATS.sectors, 'Sectors']
  ];
  h.innerHTML = pills.map(([n,l]) =>
    `<div class="stat-pill"><div class="stat-num">${{n}}</div><div class="stat-lbl">${{l}}</div></div>`
  ).join('');
}}

// ── hiring cards ──
function renderHiringCards(cos) {{
  const hiring = cos.filter(c => c.hiring === 'actively_hiring');
  document.getElementById('hiringCount').textContent = hiring.length;
  const el = document.getElementById('hiringCards');
  const none = document.getElementById('hiringNone');
  if (!hiring.length) {{ el.innerHTML=''; none.classList.remove('d-none'); return; }}
  none.classList.add('d-none');
  el.innerHTML = hiring.map(c => {{
    const tags = c.tags.slice(0,2).map(tagBadge).join(' ');
    const roles = c.roles.map(r => `<span class="role-chip">📌 ${{r.title}}</span>`).join('');
    const rolesSection = c.roles.length ? `<div class="mt-2">${{roles}}</div>` : '';
    const btn = c.careers_url
      ? `<a href="${{c.careers_url}}" target="_blank" class="btn btn-sm btn-success mt-2 py-0">View jobs ↗</a>`
      : (c.url ? `<a href="${{c.url}}" target="_blank" class="btn btn-sm btn-outline-secondary mt-2 py-0">Visit site ↗</a>` : '');
    return `<div class="col-md-6 col-lg-4 mb-1">
      <div class="hire-card">
        <h6><a href="${{c.url || '#'}}" target="_blank">${{c.name}}</a></h6>
        <div class="mb-1">${{tags}}</div>
        <div class="card-desc">${{c.desc.slice(0,140)}}${{c.desc.length>140?'…':''}}</div>
        ${{rolesSection}}${{btn}}
      </div></div>`;
  }}).join('');
}}

// ── jobs tab ──
function renderJobs(cos, jobQuery) {{
  const q = (jobQuery||'').toLowerCase();
  let roles = ALL_ROLES.filter(r => {{
    if (!cos.find(c => c.name === r.company)) return false;
    if (q && !r.title.toLowerCase().includes(q) && !r.company.toLowerCase().includes(q)) return false;
    return true;
  }});
  const jobsEl   = document.getElementById('jobsList');
  const jobsNone = document.getElementById('jobsNone');
  const countEl  = document.getElementById('jobsCount');
  countEl.textContent = roles.length;
  if (roles.length) {{
    jobsNone.classList.add('d-none');
    jobsEl.innerHTML = roles.map(r => {{
      const tags = r.tags.slice(0,2).map(tagBadge).join(' ');
      const typeLabel = r.type_ !== 'unknown' ? r.type_ : '';
      const apply = r.careers_url ? `<a href="${{r.careers_url}}" target="_blank" class="btn btn-sm btn-success py-0 ms-auto flex-shrink-0">Apply ↗</a>` : '';
      return `<div class="job-card">
        <div class="flex-grow-1">
          <div class="job-title">${{r.title}}</div>
          <div class="job-co"><a href="${{r.url}}" target="_blank">${{r.company}}</a> · ${{r.stage}}</div>
          <div class="job-meta">${{[r.location, typeLabel].filter(Boolean).join(' · ')}} &nbsp; ${{tags}}</div>
        </div>${{apply}}
      </div>`;
    }}).join('');
  }} else {{
    jobsEl.innerHTML = '';
    jobsNone.classList.remove('d-none');
  }}

  // Outreach cards
  const hasRoleNames = new Set(ALL_ROLES.map(r => r.company));
  const outreach = cos.filter(c => c.hiring === 'actively_hiring' && !hasRoleNames.has(c.name));
  document.getElementById('outreachCount').textContent = outreach.length;
  document.getElementById('outreachCards').innerHTML = outreach.map(c => {{
    const tags = c.tags.slice(0,2).map(tagBadge).join(' ');
    const mailto = c.contact ? `<a href="mailto:${{c.contact}}" class="btn btn-sm btn-outline-primary mt-2 py-0">Email ↗</a>` : '';
    const careers= c.careers_url ? `<a href="${{c.careers_url}}" target="_blank" class="btn btn-sm btn-success mt-2 py-0 ms-1">Jobs ↗</a>` : '';
    const site   = c.url ? `<a href="${{c.url}}" target="_blank" class="btn btn-sm btn-outline-secondary mt-2 py-0 ms-1">Site ↗</a>` : '';
    return `<div class="col-md-6 col-lg-4 mb-1">
      <div class="hire-card">
        <h6><a href="${{c.url || '#'}}" target="_blank">${{c.name}}</a></h6>
        <div class="mb-1">${{tags}}</div>
        <div class="card-desc">${{c.desc.slice(0,120)}}${{c.desc.length>120?'…':''}}</div>
        ${{mailto}}${{careers}}${{site}}
      </div></div>`;
  }}).join('');
}}

// ── CSV download ──
function escapeCSV(v) {{
  if (v === null || v === undefined) return '';
  const s = String(v);
  return s.includes(',') || s.includes('"') || s.includes('\\n')
    ? '"' + s.replace(/"/g, '""') + '"' : s;
}}
function triggerDownload(csv, filename) {{
  const blob = new Blob([csv], {{type: 'text/csv;charset=utf-8;'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}}
function downloadCompaniesCSV() {{
  const cos = getFiltered();
  const cols = ['name','url','stage','employees','hiring','tags_str','postcode','ch','source','hub','desc','careers_url','tech','founded'];
  const headers = ['Company','URL','Stage','Employees','Hiring Status','Sectors','Postcode','CH Verified','Source','Hub','Description','Careers URL','Tech Keywords','Founded'];
  const rows = [headers.join(',')].concat(cos.map(c => cols.map(k => escapeCSV(k==='tags_str'?c.tags.join('; '):c[k])).join(',')));
  triggerDownload(rows.join('\\n'), 'cambridge_tech_companies.csv');
}}
function downloadRolesCSV() {{
  const cos = getFiltered();
  const cosNames = new Set(cos.map(c => c.name));
  const roles = ALL_ROLES.filter(r => cosNames.has(r.company));
  const cols = ['title','company','type_','location','stage','careers_url','url'];
  const headers = ['Role','Company','Type','Location','Stage','Apply URL','Company URL'];
  const rows = [headers.join(',')].concat(roles.map(r => cols.map(k => escapeCSV(r[k])).join(',')));
  triggerDownload(rows.join('\\n'), 'cambridge_tech_roles.csv');
}}

// ── DataTable ──
let table;
$(document).ready(function() {{
  table = $('#coTable').DataTable({{
    pageLength: 50,
    order: [[4,'asc']],
    columnDefs: [{{ orderable:false, targets:[1,5,6,7] }}],
    language: {{ search:'', info:'Showing _START_–_END_ of _TOTAL_', lengthMenu:'Show _MENU_' }},
    drawCallback() {{ document.getElementById('tableCount').textContent = this.api().rows({{search:'applied'}}).count(); }}
  }});
  $('#fSearch').on('keyup', function() {{ table.search(this.value).draw(); }});
  $('#fSector').on('change', function() {{ table.column(1).search(this.value,false,true).draw(); }});
  $('#fStage').on('change',  function() {{ table.column(2).search(this.value).draw(); }});
  $('#fHiring').on('change', function() {{ table.column(4).search(this.value,false,true).draw(); }});
  $('#fSource').on('change', function() {{ table.column(7).search(this.value,false,true).draw(); }});
}});

// ── filter listeners ──
['fSearch','fSector','fStage','fHiring','fSource'].forEach(id => {{
  document.getElementById(id).addEventListener(id==='fSearch'?'input':'change', () => {{
    state.search = document.getElementById('fSearch').value;
    state.sector = document.getElementById('fSector').value;
    state.stage  = document.getElementById('fStage').value;
    state.hiring = document.getElementById('fHiring').value;
    state.source = document.getElementById('fSource').value;
    const f = getFiltered();
    renderHiringCards(f);
    updateMap(f);
    renderJobs(f, document.getElementById('jobSearch').value);
  }});
}});
document.getElementById('jobSearch').addEventListener('input', () => {{
  renderJobs(getFiltered(), document.getElementById('jobSearch').value);
}});
function resetFilters() {{
  ['fSearch','fSector','fStage','fHiring','fSource'].forEach(id => document.getElementById(id).value='');
  Object.assign(state, {{search:'',sector:'',stage:'',hiring:'',source:''}});
  if (table) table.search('').columns().search('').draw();
  const f = getFiltered();
  renderHiringCards(f);
  updateMap(f);
  renderJobs(f, '');
}}

// ── charts ──
new Chart(document.getElementById('sectorChart'),{{
  type:'bar',
  data:{{labels:STATS.tag_labels, datasets:[{{data:STATS.tag_vals, backgroundColor:'#1b3a6b', borderRadius:5}}]}},
  options:{{
    indexAxis:'y',
    plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:ctx=>' '+ctx.raw+' companies'}}}}}},
    scales:{{x:{{grid:{{display:false}},ticks:{{color:'#888'}}}},y:{{grid:{{display:false}},ticks:{{color:'#555',font:{{size:11}}}}}}}}
  }}
}});
new Chart(document.getElementById('stageChart'),{{
  type:'doughnut',
  data:{{labels:['Startup','Scaleup','Established','Unknown'],datasets:[{{data:STATS.stage_vals,backgroundColor:['#0077b6','#6a0dad','#333','#adb5bd'],borderWidth:2,borderColor:'#fff'}}]}},
  options:{{plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}},padding:10,usePointStyle:true}}}}}}}}
}});
new Chart(document.getElementById('empChart'),{{
  type:'bar',
  data:{{labels:['1-10','11-50','51-200','200-1k','1k+','?'],datasets:[{{data:STATS.emp_vals,backgroundColor:'#40916c',borderRadius:5}}]}},
  options:{{
    indexAxis:'y',
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' '+ctx.raw+' companies'}}}}}},
    scales:{{x:{{grid:{{display:false}},ticks:{{color:'#888'}}}},y:{{grid:{{display:false}},ticks:{{color:'#555',font:{{size:11}}}}}}}}
  }}
}});

// ── MAP ──
let map, markers, heatLayer;
let mapInitialised = false;
let mapMode = 'dots'; // 'dots' or 'heat'

function setMapMode(mode) {{
  mapMode = mode;
  document.getElementById('btnDots').className = mode==='dots' ? 'btn btn-sm btn-primary me-1' : 'btn btn-sm btn-outline-secondary me-1';
  document.getElementById('btnHeat').className = mode==='heat' ? 'btn btn-sm btn-primary' : 'btn btn-sm btn-outline-secondary';
  if (!mapInitialised) return;
  if (mode === 'heat') {{
    map.removeLayer(markers);
    if (heatLayer) map.addLayer(heatLayer);
  }} else {{
    if (heatLayer) map.removeLayer(heatLayer);
    map.addLayer(markers);
  }}
}}

function initMap() {{
  map = L.map('map').setView([52.19, 0.16], 10);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution:'© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
    maxZoom:18
  }}).addTo(map);
  markers = L.markerClusterGroup({{
    maxClusterRadius:40,
    showCoverageOnHover:false,
    iconCreateFunction(cluster) {{
      const n = cluster.getChildCount();
      return L.divIcon({{
        html:`<div style="background:#1b3a6b;color:#fff;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;box-shadow:0 2px 6px rgba(0,0,0,.3)">${{n}}</div>`,
        iconSize:[36,36], className:''
      }});
    }}
  }});
  map.addLayer(markers);
  mapInitialised = true;
  updateMap(getFiltered());
}}

function updateMap(cos) {{
  if (!mapInitialised) return;
  markers.clearLayers();
  const heatPoints = [];
  let shown = 0;
  cos.forEach(c => {{
    if (!c.lat || !c.lon) return;
    const col   = SCOL[c.stage] || '#888';
    const tags  = c.tags.slice(0,3).map(t=>`<span class="badge" style="background:${{TCOL[t]||'#607d8b'}};font-size:.65rem">${{t}}</span>`).join(' ');
    const hire  = c.hiring==='actively_hiring' ? ' <span class="badge bg-success">Hiring</span>' : '';
    const approx= c.loc_approx ? ' <small style="opacity:.55;font-size:.72rem">(approx location)</small>' : '';
    const jobBtn= c.careers_url ? `<br><a href="${{c.careers_url}}" target="_blank" class="btn btn-sm btn-success py-0 mt-1">View jobs ↗</a>` : '';
    const siteBtn=c.url ? `<a href="${{c.url}}" target="_blank" class="btn btn-sm btn-outline-secondary py-0 mt-1 ms-1">Site ↗</a>` : '';
    const popup = `<strong>${{c.name}}</strong>${{hire}}${{approx}}<br>${{tags}}
      <p style="margin:.4rem 0 .2rem;font-size:.8rem;color:#555">${{c.desc.slice(0,130)}}${{c.desc.length>130?'…':''}}</p>
      <small style="color:#999">${{c.stage}} · ${{c.employees}} · ${{c.postcode||'no postcode'}}</small>
      ${{jobBtn}}${{siteBtn}}`;
    const m = L.circleMarker([c.lat,c.lon],{{
      radius:7, fillColor:col, color:'#fff',
      weight:1.5, opacity:1, fillOpacity:0.88
    }}).bindPopup(popup,{{maxWidth:290}});
    markers.addLayer(m);
    heatPoints.push([c.lat, c.lon, 1]);
    shown++;
  }});

  // Rebuild heat layer
  if (heatLayer) map.removeLayer(heatLayer);
  heatLayer = L.heatLayer(heatPoints, {{
    radius: 22,
    blur: 18,
    maxZoom: 13,
    gradient: {{0.2:'#4361ee', 0.4:'#7209b7', 0.6:'#f72585', 0.8:'#ff9500', 1.0:'#ffdd00'}},
    opacity: 0.7
  }});
  if (mapMode === 'heat') map.addLayer(heatLayer);

  document.getElementById('mapCount').textContent = `${{shown}} companies`;
}}

// Init map when Map tab shown
document.querySelector('[href="#tab-map"]').addEventListener('shown.bs.tab', () => {{
  if (!mapInitialised) initMap();
  else map.invalidateSize();
}});

// ── initial render ──
renderHero();
renderHiringCards(ALL);
renderJobs(ALL, '');
</script>
</body>
</html>'''

out = SCRIPT_DIR / 'cambridge_job_board.html'
out.write_text(html, encoding='utf-8')
print(f"Written: {out}")
print(f"Size: {out.stat().st_size/1024:.0f} KB")
