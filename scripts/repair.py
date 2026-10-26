"""Repoint broken texture refs in the 3 Poly Haven files whose .blend
still points at the original artist's working directories."""
import bpy, os, json, glob

TARGETS = ["food_avocado_01", "painted_wooden_table", "flower_gazania"]
LIB = os.environ.get("KITBASH_LIBRARY", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# keyword in the broken filename -> Poly Haven channel suffix
CHANNEL = [
    (("nor_gl", "normal_flat", "normal", "norgl", "_nor"), "nor_gl"),
    (("rough",), "rough"),
    (("height", "disp"), "disp"),
    (("alpha", "opacity"), "alpha"),
    (("albedo", "basecolor", "base_color", "diff", "color"), "diff"),
]

log = {}
for name in TARGETS:
    hits = glob.glob(os.path.join(LIB, "*", name, name + ".blend"))
    if not hits:
        log[name] = "blend not found"
        continue
    path = hits[0]
    texdir = os.path.join(os.path.dirname(path), "textures")
    local = os.listdir(texdir) if os.path.isdir(texdir) else []

    def find(channel):
        for f in local:
            base = f.lower()
            # match "<asset>_<channel>_2k.<ext>"
            if f"_{channel}_" in base or base.endswith(f"_{channel}.png"):
                return f
        return None

    bpy.ops.wm.open_mainfile(filepath=path)
    fixed, unresolved = [], []
    for img in bpy.data.images:
        if img.source != "FILE" or not img.filepath:
            continue
        ap = bpy.path.abspath(img.filepath)
        if os.path.exists(ap):
            continue
        fname = os.path.basename(img.filepath).lower()
        if fname.endswith((".hdr", ".exr")) and ("hdri" in img.filepath.lower()
                                                 or "panorama" in fname
                                                 or "studiolights" in img.filepath.lower()):
            continue  # lighting HDRI from artist's machine; not a model texture
        chan = None
        for keys, c in CHANNEL:
            if any(k in fname for k in keys):
                chan = c
                break
        target = find(chan) if chan else None
        if target:
            img.filepath = "//textures/" + target
            img.reload()
            fixed.append((os.path.basename(fname), target))
        else:
            unresolved.append(fname)

    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    log[name] = {"fixed": fixed, "unresolved": unresolved}

print("REPAIR_RESULT " + json.dumps(log, indent=1))
