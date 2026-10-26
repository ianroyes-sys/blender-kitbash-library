#!/usr/bin/env python3
"""Download the full Poly Haven CC0 model library, sorted into genre folders."""
import json, os, sys, urllib.request, concurrent.futures, collections

ROOT = os.environ.get("KITBASH_LIBRARY", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = "2k"
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}

# (folder, [poly haven categories]) -- first match wins, so order = priority
GENRES = [
    ("01_Nature_and_Organic",      ["nature", "trees", "plants", "flowers", "potted plants",
                                    "succulent", "grass", "rocks", "ground cover"]),
    ("02_Industrial_and_Machinery",["industrial", "tools", "containers"]),
    ("03_Architecture_Structures", ["structures", "buildings"]),
    ("04_Vehicles_and_Ships",      ["ships"]),
    ("05_Weapons",                 ["weapons", "firearms"]),
    ("06_Characters_and_Creatures",["creature", "rigged"]),
    ("07_Furniture_and_Seating",   ["furniture", "seating", "table", "bed", "shelves"]),
    ("08_Electronics_Appliances",  ["electronics", "appliances", "lighting", "office"]),
    ("09_Food_and_Kitchen",        ["food", "dishes"]),
    ("10_Props_and_Decorative",    ["props", "decorative", "wall decoration", "vases",
                                    "books", "instrument"]),
]
FALLBACK = "10_Props_and_Decorative"


def get_json(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:
            if i == tries - 1:
                raise
    return None


def download(url, dest, tries=4):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r, open(dest + ".part", "wb") as f:
                while True:
                    chunk = r.read(262144)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(dest + ".part", dest)
            return True
        except Exception:
            if os.path.exists(dest + ".part"):
                try: os.remove(dest + ".part")
                except OSError: pass
            if i == tries - 1:
                return False
    return False


def genre_for(cats):
    cats = [c for c in cats if not c.startswith("collection:")]
    for folder, keys in GENRES:
        if any(c in keys for c in cats):
            return folder
    return FALLBACK


def handle(item):
    aid, meta = item
    folder = genre_for(meta.get("categories", []))
    base = os.path.join(ROOT, folder, aid)
    marker = os.path.join(base, ".complete")
    if os.path.exists(marker):
        return aid, folder, True, 0

    try:
        files = get_json(f"https://api.polyhaven.com/files/{aid}")
    except Exception:
        return aid, folder, False, 0

    blends = files.get("blend", {})
    res = RES if RES in blends else (sorted(blends)[0] if blends else None)
    if not res:
        return aid, folder, False, 0
    info = blends[res]["blend"]

    ok = download(info["url"], os.path.join(base, f"{aid}.blend"))
    nbytes = info["size"] if ok else 0
    for relpath, tex in info.get("include", {}).items():
        if download(tex["url"], os.path.join(base, relpath)):
            nbytes += tex["size"]
        else:
            ok = False

    if ok:
        open(marker, "w").close()
    return aid, folder, ok, nbytes


def main():
    assets = get_json("https://api.polyhaven.com/assets?type=models")
    items = list(assets.items())
    print(f"Poly Haven: {len(items)} CC0 models -> {ROOT}", flush=True)

    done = failed = 0
    total_bytes = 0
    per_genre = collections.Counter()
    fails = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for aid, folder, ok, nb in ex.map(handle, items):
            if ok:
                done += 1
                per_genre[folder] += 1
                total_bytes += nb
            else:
                failed += 1
                fails.append(aid)
            n = done + failed
            if n % 25 == 0:
                print(f"  {n}/{len(items)}  ok={done} fail={failed}  "
                      f"{total_bytes/1073741824:.2f} GB", flush=True)

    print(f"\nDONE  ok={done} failed={failed}  {total_bytes/1073741824:.2f} GB", flush=True)
    for g, n in sorted(per_genre.items()):
        print(f"  {n:4d}  {g}", flush=True)
    if fails:
        print("FAILED: " + ", ".join(fails), flush=True)
    json.dump({"downloaded": done, "failed": fails, "bytes": total_bytes,
               "per_genre": dict(per_genre)},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "polyhaven_result.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
