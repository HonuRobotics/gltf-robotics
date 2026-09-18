import json,struct,sys,urllib.request
def probe(url,label):
    d=urllib.request.urlopen(url).read()
    assert d[:4]==b'glTF', label+" not glb"
    n=struct.unpack('<I',d[12:16])[0]
    j=json.loads(d[20:20+n])
    imgs=j.get('images',[])
    mats=j.get('materials',[])
    slots={}
    for m in mats:
        p=m.get('pbrMetallicRoughness',{})
        for k,t in [('base',p.get('baseColorTexture')),('mr',p.get('metallicRoughnessTexture')),('normal',m.get('normalTexture')),('occl',m.get('occlusionTexture')),('emis',m.get('emissiveTexture'))]:
            if t is not None:
                src=j['textures'][t['index']].get('source')
                slots.setdefault(k,set()).add(imgs[src].get('mimeType','?') if src is not None else '?')
    tris=0
    for me in j.get('meshes',[]):
        for p in me.get('primitives',[]):
            if 'indices' in p: tris+=j['accessors'][p['indices']]['count']//3
    print(f"{label}: size={len(d)/1e6:.2f}MB nodes={len(j.get('nodes',[]))} meshes={len(j.get('meshes',[]))} mats={len(mats)} imgs={len(imgs)} tris={tris} ext={j.get('extensionsUsed',[])}")
    print(f"   mimetypes: {[(k,sorted(v)) for k,v in slots.items()]}  gen={j.get('asset',{}).get('generator','?')}")
for url,label in [
 ("https://raw.githubusercontent.com/gazebosim/jetty_demo/main/jetty_demo/models/Forklift/base_visual.glb","jetty/Forklift"),
 ("https://raw.githubusercontent.com/gazebosim/jetty_demo/main/jetty_demo/models/Distribution_Warehouse/base_visual.glb","jetty/Warehouse"),
 ("https://raw.githubusercontent.com/iche033/simple_warehouse/main/models/thor_table/thor_table.glb","iche033/thor_table"),
 ("https://raw.githubusercontent.com/ros-physical-ai/demos/main/pai_assets/models/Camera_Arm/camera_arm_visual.glb","pai/Camera_Arm"),
 ("https://raw.githubusercontent.com/husarion/rosbot_ros/jazzy/rosbot_description/meshes/rosbot/body.glb","husarion/rosbot_body"),
]:
    try: probe(url,label)
    except Exception as e: print(label,"ERR",e)
