#!/usr/bin/env python3
"""Write an INDEX.md inside each genre folder listing what's in it."""
import os, re, json

ROOT = os.environ.get("KITBASH_LIBRARY", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BLURB = {
    "01_Nature_and_Organic": "Trees, plants, flowers, rocks, ground cover and terrain scatter.",
    "02_Industrial_and_Machinery": "Barrels, crates, tools, pipes, containers and factory parts.",
    "03_Architecture_Structures": "Buildings, city kits, walls, towers, dungeon and cave modules.",
    "04_Vehicles_and_Ships": "Cars, spacecraft, boats, planes and racing kits.",
    "05_Weapons": "Firearms, blasters and melee weapons.",
    "06_Characters_and_Creatures": "Rigged figures, creatures and character kits.",
    "07_Furniture_and_Seating": "Chairs, tables, beds, shelves and interior furniture.",
    "08_Electronics_Appliances": "Devices, screens, lighting, office and household appliances.",
    "09_Food_and_Kitchen": "Food items, dishes and cookware.",
    "10_Props_and_Decorative": "General props, decor, vases, books, instruments, wall pieces.",
    "11_Kenney_Game_Kits": "Kenney modular game kits that span several genres.",
}

EXTS = (".blend", ".obj", ".fbx", ".gltf", ".glb", ".dae")


def pretty(name):
    n = name.replace("kenney_", "").replace("_", " ").replace("-", " ")
    n = re.sub(r"\s+", " ", n).strip()
    return n[:1].upper() + n[1:]


def scan(folder):
    """Return list of (display_name, source, formats, size_mb)."""
    out = []
    base = os.path.join(ROOT, folder)
    for entry in sorted(os.listdir(base)):
        d = os.path.join(base, entry)
        if not os.path.isdir(d) or entry.startswith("."):
            continue
        fmts, size = set(), 0
        for dp, _, fs in os.walk(d):
            for f in fs:
                if f.startswith("."):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in EXTS:
                    fmts.add(ext.lstrip("."))
                try:
                    size += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        src = "Kenney" if entry.startswith("kenney_") else "Poly Haven"
        out.append((pretty(entry), entry, src, sorted(fmts), size / 1048576))
    return out


def main():
    grand = 0
    summary = []
    for folder in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, folder)
        if not os.path.isdir(p) or folder.startswith("_") or folder.startswith("."):
            continue
        items = scan(folder)
        if not items:
            continue
        tot = sum(i[4] for i in items)
        grand += tot
        summary.append((folder, len(items), tot))

        lines = [f"# {folder.split('_', 1)[1].replace('_', ' ')}", ""]
        if folder in BLURB:
            lines += [BLURB[folder], ""]
        lines += [f"**{len(items)} assets · {tot/1024:.2f} GB**", "",
                  "All CC0 (public domain) — free for commercial use, no attribution required.", "",
                  "| Asset | Source | Formats | Size |", "|---|---|---|---|"]
        for disp, raw, src, fmts, mb in items:
            f = ", ".join(fmts) if fmts else "—"
            lines.append(f"| {disp} | {src} | {f} | {mb:.0f} MB |")
        lines.append("")
        with open(os.path.join(p, "INDEX.md"), "w") as fh:
            fh.write("\n".join(lines))
        print(f"{len(items):5d}  {tot/1024:6.2f} GB  {folder}")

    print(f"\nTOTAL {grand/1024:.2f} GB")
    json.dump(summary, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "index_summary.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
