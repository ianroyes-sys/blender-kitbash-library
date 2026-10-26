import bpy, os, glob, json
LIB=os.environ.get("KITBASH_LIBRARY", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log={}
for name in ["food_avocado_01","painted_wooden_table"]:
    path=glob.glob(os.path.join(LIB,"*",name,name+".blend"))[0]
    texdir=os.path.join(os.path.dirname(path),"textures")
    local=os.listdir(texdir)
    def find(ch):
        for f in local:
            if f"_{ch}_" in f.lower(): return f
        return None
    bpy.ops.wm.open_mainfile(filepath=path)
    fixed,left=[],[]
    for img in bpy.data.images:
        if img.source!="FILE" or not img.filepath: continue
        if os.path.exists(bpy.path.abspath(img.filepath)): continue
        fn=os.path.basename(img.filepath).lower()
        t = find("ao") if "ao" in fn else (find("arm") if "metallic" in fn else None)
        if t:
            img.filepath="//textures/"+t; img.reload(); fixed.append((fn,t))
        else:
            left.append(fn)
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    log[name]={"fixed":fixed,"left":left}
print("R2 "+json.dumps(log))
