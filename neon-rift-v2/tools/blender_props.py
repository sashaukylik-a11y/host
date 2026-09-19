import bpy, math, sys
from pathlib import Path

OUT=Path(sys.argv[-1])
OUT.mkdir(parents=True,exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def mat(name,color,metal=.0,rough=.5,emit=None):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal
    bs.inputs['Roughness'].default_value=rough
    if emit:
        bs.inputs['Emission Color'].default_value=(*emit,1)
        bs.inputs['Emission Strength'].default_value=4
    return m

dark=mat('DarkSteel',(0.04,.055,.075),.8,.25)
steel=mat('Steel',(.18,.22,.26),.72,.28)
rust=mat('Rust',(.28,.11,.045),.46,.7)
blue=mat('BlueLight',(.02,.15,.26),.45,.22,(.02,.45,1.0))
red=mat('RedLight',(.2,.015,.01),.35,.25,(1,.02,.01))
yellow=mat('Hazard',(.7,.45,.04),.35,.5)

def bevel(obj,amt=.05):
    mod=obj.modifiers.new('EdgeBevel','BEVEL');mod.width=amt;mod.segments=2
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.shade_smooth()

def cube(name,loc,scale,material):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material);bevel(o,min(scale)*.08 if min(scale)>.1 else .02);return o

def cyl(name,loc,radius,depth,material,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object;o.name=name;o.data.materials.append(material);bevel(o,.025);return o

def export(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(OUT/f'{name}.glb'),export_format='GLB',use_selection=True,export_apply=True)

clear()
cube('crate_body',(0,.55,0),(.65,.55,.65),rust)
for x in (-.58,.58):
    cube('brace',(x,.55,0),(.05,.6,.69),steel)
for z in (-.58,.58):
    cube('brace',(0,.55,z),(.69,.6,.05),steel)
export('crate')

clear()
cyl('barrel',(0,.65,0),.42,1.3,rust)
for y in (.22,.65,1.08):
    cyl('ring',(0,y,0),.44,.06,steel)
export('barrel')

clear()
cube('terminal_base',(0,.65,0),(.7,.65,.42),dark)
cube('screen',(0,1.15,-.43),(.55,.32,.035),blue)
cube('keyboard',(0,.72,-.62),(.52,.06,.22),steel)
export('terminal')

clear()
cube('generator',(0,1.0,0),(1.25,1.0,.75),dark)
for x in (-.75,0,.75):
    cyl('coil',(x,.98,-.78),.16,1.2,steel,rot=(math.pi/2,0,0))
cube('panel',(0,1.05,-.79),(.42,.34,.04),yellow)
cube('status',(0,1.58,-.8),(.28,.08,.03),blue)
export('generator')

clear()
cube('door',(0,1.4,0),(1.25,1.4,.12),dark)
for x in (-1.1,1.1):
    cube('frame',(x,1.4,0),(.12,1.55,.2),steel)
cube('header',(0,2.86,0),(1.25,.12,.2),steel)
cube('reader',(.86,1.2,-.18),(.12,.24,.05),red)
export('door')

clear()
cyl('pipe',(0,0,0),.12,2.0,rust,rot=(math.pi/2,0,0))
for z in (-.9,.9):
    cyl('clamp',(0,0,z),.15,.06,steel,rot=(math.pi/2,0,0))
export('pipe')

clear()
cube('pistol_grip',(0,-.12,.05),(.10,.22,.12),dark)
cube('pistol_slide',(0,.08,-.13),(.11,.09,.34),steel)
cyl('barrel',(0,.08,-.48),.035,.18,dark,rot=(math.pi/2,0,0))
export('pistol')
print('Blender GLB props generated:', OUT)
