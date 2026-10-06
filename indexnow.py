#!/usr/bin/env python3
"""Submit new and changed Atlas pages to IndexNow (Bing, Yandex and others) after a push.
Builds the site now and at the previous commit, compares every page, submits only what changed.
  python3 indexnow.py --before <old_sha>   changed/new pages since that commit
  python3 indexnow.py --all                every page in the sitemap
  add --dry to only print what would be sent (no waiting, no submitting)"""
import hashlib, json, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path

CFG = json.load(open("data/national.json"))
KEY, BASE = CFG["indexnow_key"], CFG["base_url"]
HOST = BASE.split("//")[1]
args = sys.argv[1:]
DRY, ALL = "--dry" in args, "--all" in args
before = args[args.index("--before") + 1] if "--before" in args else ""


def build(cwd):
    subprocess.run([sys.executable, "generate.py"], cwd=cwd, check=True, stdout=subprocess.DEVNULL)
    return Path(cwd) / "dist"


def pages(dist):
    out = {}
    for loc in re.findall(r"<loc>(.*?)</loc>", (dist / "sitemap.xml").read_text()):
        parts = [x for x in loc[len(BASE):].split("/") if x]
        f = dist.joinpath(*parts, "index.html") if loc.endswith("/") else dist.joinpath(*parts)
        if f.is_file(): out[loc] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def is_live(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "atlas-indexnow"}), timeout=20).status == 200
    except Exception:
        return False


new = pages(build("."))
old = {}
if before and not ALL and set(before) != {"0"}:
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "worktree", "add", "--detach", tmp + "/prev", before], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        old = pages(build(tmp + "/prev"))
    except Exception as ex:
        print("Could not build the previous version, submitting all pages:", ex)
urls = [u for u, h in new.items() if old.get(u) != h]
added = [u for u in urls if u not in old]
print(f"{len(new)} pages in sitemap, {len(urls)} new or changed ({len(added)} new).")
if not urls:
    sys.exit(0)
if DRY:
    print("\n".join(urls[:15]))
    sys.exit(0)

# wait for the host (Cloudflare Pages) to finish deploying before telling search engines
deadline = time.time() + 600
if added:
    while time.time() < deadline and not all(is_live(u) for u in added[:5]):
        time.sleep(20)
else:
    time.sleep(150)
if not is_live(f"{BASE}/{KEY}.txt"):
    sys.exit("The IndexNow key file is not reachable yet. Is the site deployed? Run this workflow again later.")

for i in range(0, len(urls), 10000):
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{BASE}/{KEY}.txt", "urlList": urls[i:i + 10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/IndexNow", body, {"Content-Type": "application/json; charset=utf-8"})
    try:
        print("IndexNow response:", urllib.request.urlopen(req, timeout=30).status)
    except urllib.error.HTTPError as ex:
        sys.exit(f"IndexNow error {ex.code}: {ex.read()[:200]!r}")
