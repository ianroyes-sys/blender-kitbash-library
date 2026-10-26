#!/usr/bin/env python3
"""Crawl kenney.nl, find the CC0 3D asset kits, download + unzip into genre folders."""
import json, os, re, sys, zipfile, urllib.request, concurrent.futures, collections

ROOT = os.environ.get("KITBASH_LIBRARY", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRATCH = os.path.dirname(os.path.abspath(__file__))
ZIPDIR = os.path.join(SCRATCH, "kenney_zips")
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}

# slug keyword -> genre folder. First match wins.
ROUTES = [
    ("03_Architecture_Structures", ["city-kit", "castle-kit", "tower", "building",
                                    "modular-dungeon", "modular-cave", "graveyard",
                                    "fantasy-town", "mini-dungeon", "dungeon"]),
    ("01_Nature_and_Organic",      ["nature", "forest", "farm", "food-kit", "mini-forest",
                                    "survival-kit", "fish-pack"]),
    ("04_Vehicles_and_Ships",      ["car-kit", "vehicle", "space-kit", "pirate-kit",
                                    "racing-kit", "train", "watercraft", "plane", "tank"]),
    ("05_Weapons",                 ["blaster", "weapon", "blaster-kit"]),
    ("06_Characters_and_Creatures",["character", "blocky-characters", "mini-characters",
                                    "animal", "cube-pets", "minis"]),
    ("02_Industrial_and_Machinery",["factory-kit", "industrial", "conveyor", "pipe"]),
    ("07_Furniture_and_Seating",   ["furniture", "interior"]),
    ("11_Kenney_Game_Kits",        []),   # fallback bucket
]
FALLBACK = "11_Kenney_Game_Kits"

# Minimal pre-filter only; the authoritative 3D test is the category:3D tag
# on each asset page, so we let almost everything through to be checked.
SKIP_HINTS = ("sounds", "audio", "music", "fonts", "input-prompts")


def fetch(url, tries=4, timeout=90):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception:
            if i == tries - 1:
                raise
    return b""


def crawl_slugs():
    slugs = set()
    def page(p):
        try:
            html = fetch(f"https://kenney.nl/assets/page:{p}").decode("utf-8", "ignore")
            return set(re.findall(r'/assets/([a-z0-9][a-z0-9-]+)', html))
        except Exception:
            return set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for s in ex.map(page, range(1, 15)):
            slugs |= s
    for bad in ("category", "page", "series", "tag"):
        slugs.discard(bad)
    return sorted(slugs)


def asset_info(slug):
    """Return (slug, zip_url, is3d) or None."""
    try:
        html = fetch(f"https://kenney.nl/assets/{slug}").decode("utf-8", "ignore")
    except Exception:
        return None
    m = re.search(r'(https://kenney\.nl/media/pages/assets/[^"\'\s<>]+?\.zip)', html)
    if not m:
        m = re.search(r'(/media/pages/assets/[^"\'\s<>]+?\.zip)', html)
        if not m:
            return None
        zip_url = "https://kenney.nl" + m.group(1)
    else:
        zip_url = m.group(1)
    # Kenney tags every 3D pack with a category:3D link
    is3d = "category:3D" in html
    return slug, zip_url, is3d


def genre_for(slug):
    for folder, keys in ROUTES:
        if any(k in slug for k in keys):
            return folder
    return FALLBACK


def grab(entry):
    slug, zip_url, _ = entry
    folder = genre_for(slug)
    dest = os.path.join(ROOT, folder, f"kenney_{slug}")
    if os.path.exists(os.path.join(dest, ".complete")):
        return slug, folder, True, 0
    os.makedirs(ZIPDIR, exist_ok=True)
    zpath = os.path.join(ZIPDIR, f"{slug}.zip")
    try:
        if not (os.path.exists(zpath) and os.path.getsize(zpath) > 0):
            data = fetch(zip_url, timeout=300)
            with open(zpath, "wb") as f:
                f.write(data)
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(zpath) as z:
            for member in z.namelist():
                if member.startswith("/") or ".." in member:
                    continue
                z.extract(member, dest)
        size = os.path.getsize(zpath)
        open(os.path.join(dest, ".complete"), "w").close()
        os.remove(zpath)
        return slug, folder, True, size
    except Exception as e:
        return slug, folder, False, 0


def main():
    print("crawling kenney.nl ...", flush=True)
    slugs = crawl_slugs()
    print(f"found {len(slugs)} asset slugs", flush=True)

    cands = [s for s in slugs if not any(h in s for h in SKIP_HINTS)]
    print(f"{len(cands)} after skipping 2D/audio/UI packs", flush=True)

    infos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(asset_info, cands):
            if r and r[1]:
                infos.append(r)
    three_d = [i for i in infos if i[2]]
    print(f"{len(infos)} with zips, {len(three_d)} detected as 3D", flush=True)

    targets = three_d if len(three_d) >= 10 else infos
    ok = fail = 0
    per = collections.Counter()
    fails = []
    total = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for slug, folder, good, sz in ex.map(grab, targets):
            if good:
                ok += 1; per[folder] += 1; total += sz
            else:
                fail += 1; fails.append(slug)
            print(f"  [{ok+fail}/{len(targets)}] {'OK ' if good else 'FAIL'} {slug} -> {folder}", flush=True)

    print(f"\nDONE ok={ok} fail={fail}  {total/1073741824:.2f} GB", flush=True)
    for g, n in sorted(per.items()):
        print(f"  {n:3d}  {g}", flush=True)
    if fails:
        print("FAILED: " + ", ".join(fails), flush=True)
    json.dump({"ok": ok, "failed": fails, "per_genre": dict(per),
               "packs": [t[0] for t in targets]},
              open(os.path.join(SCRATCH, "kenney_result.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
