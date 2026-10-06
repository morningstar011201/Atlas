#!/usr/bin/env python3
"""Atlas static site generator.
  python3 generate.py            -> builds only pages whose data is complete (production)
  python3 generate.py --preview  -> builds ALL pages, noindex, to check layout/links
Add a batch: fill more rows/columns in data/states.csv (or add a country file), rebuild, push.
Cloudflare Pages: build command `python3 generate.py`, output directory `dist`."""
import csv, json, sys, html, re, shutil
from pathlib import Path
from datetime import date

PREVIEW = "--preview" in sys.argv
OUT = Path("dist")
CFG = json.load(open("data/national.json"))
BASE = CFG["base_url"]
e = html.escape
LOGO = '<svg width="28" height="28" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#2b5f51"/><path d="M17 48 32 14 47 48" fill="none" stroke="#faf8f4" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="32" cy="41" r="4.2" fill="#f0d9a8"/></svg>'
T = {"paycheck-calculator": "Paycheck Calculator", "car-insurance-cost": "Car Insurance Cost", "mortgage-payment": "Mortgage Payment"}
S = {}
for r in csv.DictReader(open("data/states.csv")):
    r = {k: (v or "").strip() for k, v in r.items() if k}
    r["name"] = r["slug"].replace("-", " ").title()
    r["nb"] = [x for x in r["neighbors"].split(";") if x]
    S[r["slug"]] = r
PAGES = {}
LM = {}
FULL = []

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def money(x): return "${:,.0f}".format(x)

def live(t, s):
    if PREVIEW: return True
    r = S[s]
    if t == "paycheck-calculator":
        if not CFG["federal"].get("verified"): return False
        tt = r["tax_type"]
        return tt == "none" or (tt == "flat" and num(r["flat_rate"]) is not None) or (tt == "brackets" and bool(r["brackets"]))
    if t == "car-insurance-cost":
        return num(r["auto_premium"]) is not None and bool(r["auto_year"])
    return num(r["prop_tax_rate"]) is not None and CFG.get("mortgage_rate") is not None

def hub_live(s): return any(live(t, s) for t in T)
def type_live(t): return any(live(t, s) for s in S)

def brk(b, inc):
    t = 0
    for i, (lo, rate) in enumerate(b):
        hi = b[i + 1][0] if i + 1 < len(b) else float("inf")
        if inc > lo: t += (min(inc, hi) - lo) * rate / 100
    return t

def net(r, inc):
    f = CFG["federal"]
    fed = brk(f["brackets"], max(0, inc - f["std_deduction"]))
    fica = min(inc, f["ss_base"]) * .062 + inc * .0145
    tt = r["tax_type"]
    ti = max(0, inc - (num(r["state_deduction"]) or 0))
    st = ti * (num(r["flat_rate"]) or 0) / 100 if tt == "flat" else brk(json.loads(r["brackets"] or "[]"), ti) if tt == "brackets" else 0
    return inc - fed - fica - st

def tbl(head, rows):
    return '<div class="tw"><table><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows) + "</table></div>"

def faq(items): return "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in items)

def page(path, title, desc, body, crumbs=(), ld=(), mod=None):
    bc = '<nav class="bc">' + " › ".join(f'<a href="{h}">{e(n)}</a>' for h, n in crumbs) + "</nav>" if crumbs else ""
    robots = '<meta name="robots" content="noindex">' if PREVIEW else ""
    pv = '<p class="pv">Preview build: numbers may be placeholders.</p>' if PREVIEW else ""
    ads = ("window.loadAds=function(){var s=document.createElement('script');s.async=1;s.crossOrigin='anonymous';s.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=%s';document.head.appendChild(s)};" % CFG["adsense_client"]) if CFG["adsense_client"] else ""
    cf = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token":"%s"}\'></script>' % CFG["cf_token"]) if CFG["cf_token"] else ""
    nav = " · ".join(f'<a href="/us/{t}/">{n}</a>' for t, n in T.items() if type_live(t))
    mod = mod or str(date.today()); img = BASE + "/assets/og.png"
    graph = [{"@type": "Organization", "name": "Atlas by RapidTool", "url": BASE + "/"}]
    if crumbs:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + h} for i, (h, n) in enumerate(list(crumbs) + [(path, title)])]})
    jl = json.dumps({"@context": "https://schema.org", "@graph": graph + list(ld)})
    PAGES[path] = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{BASE}{path}">{robots}
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{BASE}{path}"><meta property="og:type" content="website"><meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{img}">
<meta property="article:modified_time" content="{mod}"><script type="application/ld+json">{jl}</script>
<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><link rel="manifest" href="/assets/site.webmanifest"><meta name="theme-color" content="#faf8f4"><link rel="stylesheet" href="/assets/style.css"><script>{ads}</script>{cf}</head><body>
<header><a class="logo" href="/">{LOGO}Atlas</a><span>{nav}</span></header><main>{bc}{pv}{body}</main>
<footer><a href="/us/">All US states</a> · <a href="/about/">About</a> · <a href="/privacy/">Privacy</a> · <a href="/terms/">Terms</a> · <a href="/disclaimer/">Disclaimer</a></footer>
<div id="cb" class="cb"><span>We use cookies for analytics and ads. See our <a href="/privacy/">privacy policy</a>.</span><button data-c="yes">Accept</button><button data-c="no">Decline</button></div>
<script src="/assets/app.js" defer></script></body></html>"""

def links(t, s):
    r = S[s]
    sib = [f'<a href="/us/{s}/{x}/">{T[x]} in {r["name"]}</a>' for x in T if x != t and live(x, s)]
    rel = [f'<a href="/us/{n}/{t}/">{S[n]["name"]}</a>' for n in r["nb"] if n in S and live(t, n)]
    first = " · ".join(sib + [f'<a href="/us/{s}/">All {r["name"]} pages</a>', f'<a href="/us/{t}/">{T[t]} by state</a>'])
    return f"<section><h2>Keep exploring</h2><p>{first}</p>" + (f"<p>Nearby states: {' · '.join(rel)}</p>" if rel else "") + "</section>"

def state_page(t, s):
    r = S[s]; n = r["name"]; path = f"/us/{s}/{t}/"; data = {}
    nbs = [k for k in r["nb"] if k in S and live(t, k)]
    nm = lambda k: n if k == s else f'<a href="/us/{k}/{t}/">{S[k]["name"]}</a>'
    if t == "paycheck-calculator":
        f = CFG["federal"]; tt = r["tax_type"]; v = net(r, 60000)
        title = f"{n} Paycheck Calculator 2026: Take-Home Pay After Tax"
        desc = f"Estimate take-home pay in {n} after federal tax, FICA and state tax, see six salary levels and compare {n} with nearby states."
        taxdesc = {"none": "none on wages", "flat": f"flat {r['flat_rate']}%", "brackets": "progressive brackets"}.get(tt, "pending verification")
        answer = f"Take-home pay in {n} is what you keep after federal income tax, FICA and {n} state tax. On a $60,000 salary, estimated take-home pay is about {money(v)} per year ({money(v / 12)} per month)."
        pk = sorted([k for k in S if live(t, k)], key=lambda k: -key(t, k)); rk = pk.index(s) + 1 if s in pk else 0
        tl = [f"Take-home on $60,000: about {money(v)} per year ({(60000 - v) / 600:.1f}% goes to federal tax, state tax and FICA)", f"Rank: {rk} of {len(pk)} states for take-home pay on $60,000, highest first", f"{n} state income tax: {taxdesc}", "Federal income tax and FICA apply in every state", "Estimates assume a single filer and exclude local taxes"]
        tool = '<form id="f"><label>Annual salary ($)<input id="s" type="number" min="0" max="10000000" step="1000" value="60000"></label></form><p id="o" class="out"></p>'
        th = "Take-home pay at common salaries"
        tab = tbl(["Salary", "Take-home / year", "Per month", "Taxes + FICA"], [[money(x), money(net(r, x)), money(net(r, x) / 12), money(x - net(r, x))] for x in (30000, 45000, 60000, 80000, 100000, 150000)])
        ch = ["State", "Take-home on $60,000", "Per month"]
        crow = [[nm(k), money(net(S[k], 60000)), money(net(S[k], 60000) / 12)] for k in [s] + nbs]
        how = {"none": f"{n} does not tax wage income at the state level, so take-home pay is reduced mainly by federal income tax and FICA payroll taxes.",
               "flat": f"{n} uses a flat state income tax rate of {r['flat_rate']}%, applied on top of federal income tax and FICA.",
               "brackets": f"{n} uses progressive state income tax brackets: higher slices of income are taxed at higher rates, on top of federal tax and FICA."}.get(tt, f"State tax data for {n} is pending verification.")
        inc = ["Federal income tax for a single filer using the standard deduction", "Social Security and Medicare (FICA) payroll tax", f"{n} state income tax from the published rate schedule, after the state standard deduction and personal exemption where they are plain deductions", "Not included: local taxes, state payroll taxes such as disability or family-leave contributions, state credits, pre-tax deductions or other filing statuses"]
        faqs = [(f"Does the {n} paycheck calculator include local taxes?", "No. Some cities and counties add local income tax, and some states add payroll taxes for disability or family leave. This estimate covers federal tax, FICA and state income tax for a single filer using the federal standard deduction, without state credits."),
                ("How exact is this take-home pay estimate?", "It is an estimate. Pre-tax deductions, credits, filing status and your employer's withholding method will change the result."),
                ("Can I use this calculator to file taxes?", "No. It is for planning only. See the disclaimer.")]
        src = f'Federal: <a href="https://www.irs.gov/">IRS</a>, tax year {f.get("year", 2026)}. State: <a href="https://taxfoundation.org/data/all/state/state-income-tax-rates-2026/">Tax Foundation</a> 2026 rate tables, adjusted for rate changes enacted since publication.'
        data = {"t": "p", "tt": tt, "rate": num(r["flat_rate"]) or 0, "br": json.loads(r["brackets"] or "[]"), "fed": f["brackets"], "std": f["std_deduction"], "ssb": f["ss_base"], "sd": num(r["state_deduction"]) or 0}
    elif t == "car-insurance-cost":
        allp = {k: num(x["auto_premium"]) for k, x in S.items() if num(x["auto_premium"]) is not None}
        order = sorted(allp, key=lambda k: -allp[k]); p = num(r["auto_premium"]); yr = r["auto_year"] or "latest"
        mean = CFG["auto_national_avg"]
        title = f"Average Car Insurance Cost in {n} ({yr})"
        desc = f"See the average car insurance premium in {n} ({yr}), how it ranks among US states, how it compares with nearby states, and why quotes vary."
        if p is None or not mean:
            answer = f"Average car insurance cost in {n} is the typical annual premium paid by drivers in the state. Data for {n} is pending verification."; tl = ["Data pending verification"]
        else:
            rank = order.index(s) + 1; diff = (p - mean) / mean * 100
            answer = f"Average car insurance cost in {n} is the typical annual premium per insured vehicle for a policy with liability, collision and comprehensive coverage: about {money(p)} per year ({yr} NAIC data). That is {abs(diff):.0f}% {'above' if diff >= 0 else 'below'} the national average of {money(mean)} and ranks {rank} of {len(allp)} states, highest first."
            tl = [f"Average premium: {money(p)} per year, about {money(p / 12)} per month", f"Rank: {rank} of {len(allp)} states, highest first", f"Data year: {yr} (NAIC)", "Your quote depends on age, vehicle, record and coverage"]
        tool = f'<p class="out">Roughly {money(p / 12)} per month.</p>' if p else ""
        th = "Highest and lowest average premiums"
        tab = tbl(["State", "Average annual premium"], [[nm(k), money(allp[k])] for k in dict.fromkeys(order[:3] + order[-3:]) if live(t, k)])
        ch = ["State", "Average annual premium"]
        crow = [[nm(k), money(allp[k])] for k in [s] + nbs if k in allp]
        how = f"This page shows the average annual auto insurance premium in {n} from NAIC data for {yr}. Your own price depends on age, driving record, vehicle, ZIP code and coverage. NAIC cautions that state averages reflect different coverage choices, vehicle values and state laws, so compare states with care."
        inc = [f"The average annual premium per insured vehicle in {n} for liability, collision and comprehensive coverage combined", "A comparison with the national average and with nearby states", "Not included: your personal rating factors, discounts or specific coverage choices"]
        faqs = [(f"Why is my car insurance quote different from the {n} average?", "Insurers price by driver, vehicle, location and coverage. A state average is a benchmark, not a quote."),
                ("How old is this car insurance data?", f"The latest NAIC report available covers {yr}, so current premiums are likely different."),
                ("How can I pay less for car insurance?", "Compare quotes from several insurers, ask about discounts and review your coverage levels.")]
        src = 'NAIC (<a href="https://content.naic.org/">National Association of Insurance Commissioners</a>) 2022/2023 Auto Insurance Database Report, adopted December 2025: combined average premium per insured vehicle, 2023.'
    else:
        pr = num(r["prop_tax_rate"]); mr = CFG.get("mortgage_rate")
        title = f"Mortgage Payment in {n}: Calculator With Property Tax"
        desc = f"Estimate a monthly mortgage payment in {n} using its property tax rate, with examples at four home prices and a nearby-state comparison."
        m = (mr or 0) / 1200; vals = []
        for price in (200000, 300000, 400000, 500000):
            L = price * .8; pi = L * m / (1 - (1 + m) ** -360) if m else L / 360; tx = price * (pr or 0) / 1200; vals.append((price, pi, tx))
        answer = f"A monthly mortgage payment in {n} combines principal, interest and property tax. The estimated property tax rate in {n} is {pr}% of home value per year, about {money(400000 * (pr or 0) / 100)} on a $400,000 home."
        pk = sorted([k for k in S if live(t, k)], key=lambda k: -(num(S[k]["prop_tax_rate"]) or 0)); rk = pk.index(s) + 1 if s in pk else 0
        tl = [f"Property tax rate: {pr}% of home value per year, ranked {rk} of {len(pk)} states, highest first", f"Example: about {money(vals[2][1] + vals[2][2])} per month on a $400,000 home (20% down, 30 years)", "Add homeowners insurance in the calculator for a fuller estimate"]
        tool = f'<form id="f"><label>Home price ($)<input id="p" type="number" min="0" step="5000" value="400000"></label><label>Down payment (%)<input id="d" type="number" min="0" max="100" value="20"></label><label>Interest rate (%)<input id="r" type="number" min="0" max="20" step="0.01" value="{"" if mr is None else mr}"></label><label>Term (years)<input id="y" type="number" min="1" max="40" value="30"></label><label>Home insurance ($/year, optional)<input id="i" type="number" min="0" value="0"></label></form><p id="o" class="out"></p>'
        th = "Monthly payment at common home prices (20% down, 30 years)"
        tab = tbl(["Home price", "Principal + interest", "Property tax", "Total"], [[money(a), money(b), money(c), money(b + c)] for a, b, c in vals])
        ch = ["State", "Property tax rate", "Tax on a $400,000 home"]
        crow = [[nm(k), f'{num(S[k]["prop_tax_rate"])}%', money(400000 * num(S[k]["prop_tax_rate"]) / 100)] for k in [s] + nbs if num(S[k]["prop_tax_rate"]) is not None]
        how = f"Property tax in {n} is estimated at {pr}% of home value per year. Your payment also depends on price, down payment, interest rate, term and homeowners insurance, which you can enter above."
        inc = ["Principal and interest on a fixed-rate loan", f"{n} property tax at the state's estimated rate", "Optional homeowners insurance that you enter", "Not included: HOA fees, private mortgage insurance, closing costs"]
        faqs = [(f"Does this {n} mortgage calculator include homeowners insurance?", "Only if you enter it in the calculator. Insurance varies by home and location."),
                ("Is the mortgage interest rate current?", f"The default is the national weekly average as of {CFG['mortgage_rate_date'] or 'the latest update'}. Your lender's rate will differ."),
                ("What about HOA fees and PMI?", "They are not included. With under 20% down, private mortgage insurance may add to the payment.")]
        src = f'Property tax: <a href="https://taxfoundation.org/data/all/state/property-taxes-by-state-county/">Tax Foundation</a> effective rates, based on <a href="https://www.census.gov/programs-surveys/acs">US Census Bureau American Community Survey</a> 2024 data. Mortgage rate: <a href="https://www.freddiemac.com/pmms">{CFG["mortgage_rate_source"]}</a>, national average.'
        data = {"t": "m", "prop": pr or 0}
    mod = r["verified"] or str(date.today())
    cmp = f"<h2>{n} vs nearby states</h2>{tbl(ch, crow)}" if len(crow) > 1 else ""
    faqh = "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in faqs)
    tlh = "".join(f"<li>{x}</li>" for x in tl); inch = "".join(f"<li>{x}</li>" for x in inc)
    chk = "Compiled from the sources above." if r["verified"] else "Data update pending."
    srcbox = f'<div class="src"><b>Sources.</b> {src} {chk} Data last updated: {e(r["verified"] or "pending")}.</div>'
    djs = f'<script type="application/json" id="dt">{json.dumps(data)}</script>' if data else ""
    org = {"@type": "Organization", "name": "Atlas by RapidTool"}
    ld = [{"@type": "Article", "headline": title, "datePublished": mod, "dateModified": mod, "author": org, "publisher": org},
          {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
          {"@type": "Dataset", "name": title, "description": desc, "creator": org} if t == "car-insurance-cost" else
          {"@type": "WebApplication", "name": title, "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}]
    body = (f'<h1>{e(title)}</h1><p class="by">By Atlas by RapidTool · Updated <time datetime="{mod}">{mod}</time></p>'
            f'<p class="ans">{answer}</p><div class="tldr"><b>Key takeaways</b><ul>{tlh}</ul></div>{tool}'
            f'<h2>{th}</h2>{tab}{cmp}<h2>How it works in {n}</h2><p>{how}</p><h2>What this estimate includes</h2><ul>{inch}</ul>'
            f'<h2>Common questions</h2>{faqh}{srcbox}<p class="note">Estimates for planning only. See the <a href="/disclaimer/">disclaimer</a>.</p>{links(t, s)}{djs}')
    if r["verified"]: LM[path] = r["verified"]
    FULL.append((path, title, answer, tl, re.sub(r"<[^>]+>", "", src), mod))
    page(path, title, desc, body, [("/", "Atlas"), ("/us/", "United States"), (f"/us/{s}/", n)], ld, mod)

def key(t, s):
    r = S[s]
    return net(r, 60000) if t == "paycheck-calculator" else (num(r["auto_premium"]) if t == "car-insurance-cost" else num(r["prop_tax_rate"])) or 0

def hubs():
    live_t = [t for t in T if type_live(t)]
    tl = "".join(f'<li><a href="/us/{t}/">{T[t]} by state</a></li>' for t in live_t)
    page("/", "Atlas: US State Money Calculators and Cost Data", "Compare take-home pay, car insurance costs and mortgage payments for every US state, with the data source and last-verified date shown on every page.",
         f"<h1>US state money calculators and cost data</h1><p class=\"ans\">Compare take-home pay, car insurance costs and mortgage payments state by state, with the source and date shown on every page.</p><ul>{tl or '<li>Launching soon.</li>'}</ul><p><a href=\"/us/\">Browse all US states</a></p>")
    sl = "".join(f'<li><a href="/us/{s}/">{S[s]["name"]}</a></li>' for s in S if hub_live(s))
    page("/us/", "US State Money Calculators and Cost Data", "Pick a US state to see take-home pay after tax, average car insurance cost and monthly mortgage payment estimates, with sources and dates shown.",
         f"<h1>United States</h1><p>Pick a state, or browse by topic.</p><ul>{tl}</ul><h2>States</h2><ul class=\"list\">{sl}</ul>", [("/", "Atlas")])
    for s in S:
        if not hub_live(s): continue
        n = S[s]["name"]; ts = "".join(f'<li><a href="/us/{s}/{t}/">{T[t]} in {n}</a></li>' for t in T if live(t, s))
        nb = " · ".join(f'<a href="/us/{x}/">{S[x]["name"]}</a>' for x in S[s]["nb"] if x in S and hub_live(x))
        page(f"/us/{s}/", f"{n}: Paycheck, Car Insurance and Mortgage Estimates", f"Take-home pay after tax, average car insurance cost and monthly mortgage payment estimates for {n}, with data sources and verification dates.",
             f"<h1>{n}</h1><ul>{ts}</ul>" + (f"<p>Nearby states: {nb}</p>" if nb else ""), [("/", "Atlas"), ("/us/", "United States")])
    labels = {"paycheck-calculator": ("Take-home on $60,000", money), "car-insurance-cost": ("Average annual premium", money), "mortgage-payment": ("Property tax rate", lambda x: f"{x}%")}
    for t in live_t:
        lab, fm = labels[t]; ss = sorted([s for s in S if live(t, s)], key=lambda s: -key(t, s))
        rows = [[f'<a href="/us/{s}/{t}/">{S[s]["name"]}</a>', fm(key(t, s))] for s in ss]
        page(f"/us/{t}/", f"{T[t]} by US State: Ranked Comparison", f"{T[t]} compared across US states, ranked highest first, with the source and date for each figure and links to every state page.", f"<h1>{T[t]} by state</h1><p>Highest first. Pick a state for the full page.</p>{tbl(['State', lab], rows)}", [("/", "Atlas"), ("/us/", "United States")])

LEGAL = {
 "privacy": ("Privacy Policy", ["Atlas does not ask for accounts or personal information. Numbers you type into the calculators stay in your browser.",
   "This site may use cookies for visit counts and for ads shown by third parties such as Google. Third-party vendors, including Google, use cookies to serve ads based on a visitor's earlier visits to this and other websites. You can opt out of personalized advertising at <a href=\"https://adssettings.google.com\">adssettings.google.com</a> or <a href=\"https://www.aboutads.info\">aboutads.info</a>.",
   "You can decline cookies with the banner on the site. This site is not directed at children under 13.",
   "Last updated October 5, 2026."]),
 "terms": ("Terms of Use", ["Atlas gives general information and estimates. Use it at your own risk.",
   "Data comes from third-party sources and may be out of date or contain errors. The site is provided as is, without warranties. These terms may change at any time."]),
 "disclaimer": ("Disclaimer", ["Atlas is not financial, tax, insurance or legal advice. Results are estimates based on public data and simplified assumptions, such as a single filer using the standard deduction.",
   "Check figures with official sources or a qualified professional before making decisions."]),
 "about": ("About Atlas", ["Atlas is a reference for US state-level money data: take-home pay, car insurance costs and mortgage payments. It is part of RapidTool.",
   "Each page names its data sources and when its data was last updated."]),
}

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    for s in S:
        for t in T:
            if live(t, s): state_page(t, s)
    hubs()
    for k, (title, ps) in LEGAL.items():
        page(f"/{k}/", f"{title} | Atlas by RapidTool - US State Money Data", f"{title}: Atlas by RapidTool is a free reference for US state take-home pay, car insurance cost and mortgage payment estimates.", f"<h1>{title}</h1>" + "".join(f"<p>{p}</p>" for p in ps))
    page("/404.html", "Page not found | Atlas", "This page does not exist.", "<h1>Page not found</h1><p>Try a topic or browse all states.</p><p><a href=\"/us/\">All US states</a> · <a href=\"/\">Home</a></p>")
    shutil.copytree("static", OUT / "assets"); shutil.copy("static/favicon.ico", OUT / "favicon.ico")
    for p, h in PAGES.items():
        f = OUT / "404.html" if p == "/404.html" else OUT / p.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(h, encoding="utf-8")
    urls = [p for p in PAGES if p != "/404.html"]
    for f in sorted(Path("pages").rglob("*.html")) if Path("pages").is_dir() else []:
        rel = f.relative_to("pages"); txt = f.read_text(encoding="utf-8")
        (OUT / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, OUT / rel)
        d = rel.parent.as_posix(); u = ("/" if d == "." else f"/{d}/") if rel.name == "index.html" else f"/{rel.as_posix()}"
        if "noindex" not in txt and u not in urls and rel.name != "404.html": urls.append(u)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{BASE}{p}</loc>" + (f"<lastmod>{LM[p]}</lastmod>" if p in LM else "") + "</url>" for p in urls) + "</urlset>")
    BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "anthropic-ai", "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot", "Amazonbot", "Googlebot", "Bingbot"]
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n" if PREVIEW else "".join(f"User-agent: {b}\nAllow: /\n\n" for b in BOTS) + f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    fact = {"paycheck-calculator": lambda s: f"take-home on $60,000 about {money(net(S[s], 60000))} per year",
            "car-insurance-cost": lambda s: f"average annual premium {money(num(S[s]['auto_premium']))} ({S[s]['auto_year']} NAIC data)",
            "mortgage-payment": lambda s: f"estimated property tax rate {S[s]['prop_tax_rate']}% of home value per year"}
    L = ["# Atlas by RapidTool", "", "> Free reference for US state money data: take-home pay after tax, average car insurance cost and monthly mortgage payments with property tax, one page per state. Every page names its data source and last-updated date.", "", "Notes for AI assistants: figures are planning estimates, not tax, insurance or legal advice. When quoting, please cite the page URL and the data year.", ""]
    for t in T:
        ss = [s for s in sorted(S) if live(t, s)]
        if ss:
            L += [f"## {T[t]} by state", ""] + [f"- [{S[s]['name']}]({BASE}/us/{s}/{t}/): {fact[t](s)}" for s in ss] + [""]
    L += ["## Data sources", "", "- IRS and Tax Foundation: federal and state income tax rates and brackets, 2026", "- NAIC 2022/2023 Auto Insurance Database Report: 2023 combined average premium per insured vehicle", "- Tax Foundation effective property tax rates, based on US Census Bureau ACS 2024 data", "- Freddie Mac Primary Mortgage Market Survey: national weekly 30-year rate", "", "## Optional", "", f"- [Full page data in one file]({BASE}/llms-full.txt)", f"- [Sitemap]({BASE}/sitemap.xml)", f"- [About]({BASE}/about/)", f"- [Disclaimer]({BASE}/disclaimer/)", ""]
    (OUT / "llms.txt").write_text("\n".join(L), encoding="utf-8")
    F = ["# Atlas by RapidTool: full page data", "", "Plain-text copy of every state page for AI assistants. Estimates only; see the disclaimer.", ""]
    for path, title, answer, tl, src, mod in sorted(FULL):
        F += [f"## {title}", f"URL: {BASE}{path}", f"Data last updated: {mod}", "", answer, ""] + [f"- {x}" for x in tl] + ["", f"Sources: {src}", ""]
    (OUT / "llms-full.txt").write_text("\n".join(F), encoding="utf-8")
    bad = [(p, l) for p, h in PAGES.items() for l in set(re.findall(r'href="(/[^"#?]*)"', h)) if not (l in PAGES or (OUT / l.lstrip("/")).is_file())]
    iss, wc = [], []
    for p, h in PAGES.items():
        if p == "/404.html": continue
        ti = html.unescape(re.search(r"<title>(.*?)</title>", h).group(1)); de = html.unescape(re.search(r'name="description" content="(.*?)"', h).group(1))
        if not 30 <= len(ti) <= 70: iss.append((p, "title", len(ti)))
        if not 120 <= len(de) <= 170: iss.append((p, "desc", len(de)))
        if h.count("<h1") != 1: iss.append((p, "h1"))
        if p.count("/") == 4: wc.append(len(re.sub(r"<[^>]+>", " ", h).split()))
    print(f"SEO audit issues: {len(iss)} {iss[:6]} | state page words min/avg: {min(wc) if wc else 0}/{sum(wc) // max(len(wc), 1)}")
    cnt = {t: sum(live(t, s) for s in S) for t in T}
    print(f"{len(PAGES)} pages built {'(preview)' if PREVIEW else ''}; state pages live: {cnt}; broken internal links: {len(bad)}")
    for b in bad[:10]: print("  BROKEN", b)
    for k in ("adsense_client", "cf_token"):
        if not CFG[k]: print(f"  NOTE: set '{k}' in data/national.json")
    if bad: sys.exit(1)

main()
