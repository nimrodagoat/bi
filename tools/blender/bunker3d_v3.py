"""3D test v3: v2's details at the YouTube Shorts size (1080x1920), with faster render settings
and a nicer finish (glow on lights, a soft vignette). Was v2: the back-yard bunker with much more detail. A diorama cut
open at the front; a furnished steel-pipe bunker drops into a trench, the dirt is
filled back in, and three toy wizards with faces, arms and staffs pop in.
Run with Blender's Python (bpy 4.2):
python bunker3d_v2.py OUT_DIR [--still FRAME] [--samples N] [--scale PCT] [--start F --end F]"""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[1:]


def opt(name, default, cast=int):
    return cast(args[args.index(name) + 1]) if name in args else default


OUT = Path(args[0])
STILL = opt("--still", None)
SAMPLES = opt("--samples", 32)
SCALE = opt("--scale", 100)
START, END = opt("--start", 1), opt("--end", None)
FPS, FRAMES = 30, 150
rng = random.Random(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 2
scene.cycles.transmission_bounces = 2
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.sample_clamp_indirect = 3.0
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.03
scene.render.use_persistent_data = True
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = SCALE
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"


# ------------------------------------------------------------------ helpers

def principled(m):
    return m.node_tree.nodes["Principled BSDF"]


def mat(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, noise=None, bump=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = principled(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if noise:  # mottled colour
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise[0]
        tex.inputs["Detail"].default_value = 8
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*noise[1], 1)
        ramp.color_ramp.elements[1].color = (*color, 1)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        if bump:
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            nt.links.new(tex.outputs["Fac"], bp.inputs["Height"])
            nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def corrugated(name, color):
    m = mat(name, color, rough=0.3, metal=0.9)
    nt = m.node_tree
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 22
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.7
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], principled(m).inputs["Normal"])
    return m


def strata(name):
    """Soil in layers: colour bands by height, broken up by noise, with a bumpy surface."""
    m = mat(name, (0.4, 0.25, 0.13), rough=0.95)
    nt = m.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 0.35
    nt.links.new(noise.outputs["Fac"], add.inputs[0])
    nt.links.new(sep.outputs["Z"], add.inputs[2])
    scale = nt.nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = -0.075
    nt.links.new(add.outputs["Value"], scale.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.45, 0.29, 0.15, 1)
    cr.elements[1].position = 0.18
    cr.elements[1].color = (0.36, 0.22, 0.11, 1)
    for pos, col in ((0.4, (0.5, 0.36, 0.2)), (0.55, (0.3, 0.18, 0.09)), (0.78, (0.34, 0.3, 0.26))):
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    nt.links.new(scale.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], principled(m).inputs["Base Color"])
    grit = nt.nodes.new("ShaderNodeTexNoise")
    grit.inputs["Scale"].default_value = 40
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    nt.links.new(grit.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], principled(m).inputs["Normal"])
    return m


def checker(name, a, b, scale):
    m = mat(name, a, rough=0.4)
    nt = m.node_tree
    ch = nt.nodes.new("ShaderNodeTexChecker")
    ch.inputs["Color1"].default_value = (*a, 1)
    ch.inputs["Color2"].default_value = (*b, 1)
    ch.inputs["Scale"].default_value = scale
    nt.links.new(ch.outputs["Color"], principled(m).inputs["Base Color"])
    return m


def box(name, loc, size, material, bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def cyl(name, loc, r, depth, material, rot=(0, 0, 0), verts=32, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    smooth(o)
    if parent:
        o.parent = parent
    return o


def sphere(name, loc, r, material, scale=(1, 1, 1), parent=None, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    smooth(o)
    if parent:
        o.parent = parent
    return o


def cut(target, cutter):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def pop_in(o, frame, size=1.0):
    o.scale = (0.001,) * 3
    o.keyframe_insert("scale", frame=frame)
    o.scale = (size * 1.15,) * 3
    o.keyframe_insert("scale", frame=frame + 6)
    o.scale = (size,) * 3
    o.keyframe_insert("scale", frame=frame + 10)


# ------------------------------------------------------------------ materials

GRASS = mat("grass", (0.2, 0.58, 0.14), noise=(30, (0.12, 0.4, 0.08)), bump=0.4)
SOIL = strata("soil")
ROCK = mat("rock", (0.42, 0.4, 0.38), rough=0.8, noise=(8, (0.3, 0.29, 0.28)), bump=0.5)
ROOT = mat("root", (0.3, 0.2, 0.12), rough=0.9)
STEEL = corrugated("steel", (0.66, 0.69, 0.72))
STEEL_DARK = mat("steel_dark", (0.3, 0.32, 0.35), rough=0.4, metal=0.9)
WOOD = mat("wood", (0.58, 0.36, 0.18), rough=0.6, noise=(25, (0.44, 0.26, 0.12)), bump=0.2)
WALL = mat("wall", (0.9, 0.87, 0.8))
TRIM = mat("trim", (0.97, 0.97, 0.95))
ROOF = mat("roof", (0.62, 0.2, 0.14), noise=(14, (0.5, 0.15, 0.1)))
BRICK = mat("brick", (0.55, 0.22, 0.16), noise=(20, (0.42, 0.16, 0.12)))
WINDOW = mat("window", (0.15, 0.3, 0.5), rough=0.05, metal=0.2)
LEAF = mat("leaf", (0.16, 0.45, 0.12), noise=(6, (0.1, 0.32, 0.07)), bump=0.3)
BARK = mat("bark", (0.32, 0.2, 0.12), noise=(18, (0.22, 0.14, 0.08)))
FLOWER = [mat("flower1", (0.95, 0.35, 0.45)), mat("flower2", (1.0, 0.85, 0.2)), mat("flower3", (0.6, 0.45, 0.95))]
SKIN = mat("skin", (0.96, 0.82, 0.7), rough=0.5)
EYE = mat("eye", (0.02, 0.02, 0.02), rough=0.2)
BEARD = mat("beard", (0.97, 0.97, 0.97), rough=0.9)
STAFF = mat("staff", (0.38, 0.22, 0.1), rough=0.7)
ORB = mat("orb", (0.6, 0.85, 1.0), emit=(0.55, 0.85, 1.0), strength=10)
STAR = mat("star", (1.0, 0.8, 0.25), emit=(1.0, 0.75, 0.2), strength=3)
GOLD = mat("gold", (1.0, 0.78, 0.2), rough=0.25, metal=1.0)
LAMP = mat("lamp", (1, 0.9, 0.7), emit=(1, 0.85, 0.6), strength=15)
BLANKETS = [mat("blanket1", (0.25, 0.4, 0.75)), mat("blanket2", (0.75, 0.3, 0.3))]
PILLOW = mat("pillow", (0.95, 0.95, 0.92))
CANS = [mat("can1", (0.8, 0.2, 0.15), metal=0.6, rough=0.3), mat("can2", (0.2, 0.55, 0.3), metal=0.6, rough=0.3),
        mat("can3", (0.95, 0.75, 0.2), metal=0.6, rough=0.3)]
WATER = mat("water", (0.35, 0.65, 0.95), rough=0.1)
RUG = mat("rug", (0.65, 0.18, 0.2), noise=(12, (0.5, 0.12, 0.15)))
BOARD = checker("board", (0.95, 0.92, 0.85), (0.15, 0.12, 0.1), 8)
ROBES = [mat("robe1", (0.34, 0.2, 0.66)), mat("robe2", (0.13, 0.42, 0.66)), mat("robe3", (0.6, 0.15, 0.32))]

# ------------------------------------------------------------------ the ground (cut face at y = 0)

W_, D_, H_ = 40.0, 30.0, 16.0
soil = box("soil", (0, D_ / 2, -H_ / 2), (W_, D_, H_), SOIL)
lawn = box("lawn", (0, D_ / 2, 0.1), (W_ + 0.04, D_ + 0.04, 0.2), GRASS)

PIPE_R, PIPE_Z, PIPE_LEN = 1.6, -3.4, 9.0
SHAFT_X, VENT_X = -3.3, 3.4


def trench_cutter():
    bpy.ops.mesh.primitive_cube_add(location=(0, 0.9, PIPE_Z / 2 + 0.2))
    c = bpy.context.object
    c.scale = ((PIPE_LEN + 0.12) / 2, 0.9, (-PIPE_Z + 0.6) / 2)
    bpy.ops.object.transform_apply(scale=True)
    return c


bpy.ops.mesh.primitive_cylinder_add(radius=PIPE_R + 0.06, depth=PIPE_LEN + 0.1, vertices=128,
                                    location=(0, 0, PIPE_Z), rotation=(0, math.pi / 2, 0))
cut(soil, bpy.context.object)
cut(soil, trench_cutter())
cut(lawn, trench_cutter())

# stones and roots on the cut face
for i in range(26):
    x = rng.uniform(-9, 9)
    z = rng.uniform(-11, -0.8)
    if abs(x) < 5 and -5.6 < z < 0.2:
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.12, 0.45), subdivisions=2, location=(x, 0.03, z))
    st = bpy.context.object
    st.scale = (rng.uniform(1, 1.6), 0.5, rng.uniform(0.6, 1.0))
    st.rotation_euler = (0, rng.uniform(0, 3), 0)
    st.data.materials.append(ROCK)
for i in range(6):
    x0 = rng.choice([-1, 1]) * rng.uniform(5.5, 8.5)
    pts = [(x0, 0.02, -0.25)]
    for k in range(4):
        px, _, pz = pts[-1]
        pts.append((px + rng.uniform(-0.5, 0.5), 0.02, pz - rng.uniform(0.4, 0.8)))
    curve = bpy.data.curves.new(f"root{i}", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.05
    sp = curve.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(sp.points, pts):
        p.co = (x, y, z, 1)
    ob = bpy.data.objects.new(f"root{i}", curve)
    ob.data.materials.append(ROOT)
    bpy.context.collection.objects.link(ob)

# ------------------------------------------------------------------ the bunker (drops in as one piece)

bpy.ops.mesh.primitive_cylinder_add(radius=PIPE_R, depth=PIPE_LEN, vertices=160, location=(0, 0, 0),
                                    rotation=(0, math.pi / 2, 0))
pipe = bpy.context.object
pipe.name = "pipe"
bpy.ops.object.transform_apply(rotation=True)
shell = pipe.modifiers.new("shell", "SOLIDIFY")
shell.thickness = 0.12
bpy.ops.object.modifier_apply(modifier="shell")
bpy.ops.mesh.primitive_cube_add(location=(0, -2.5, 0))
c = bpy.context.object
c.scale = (PIPE_LEN, 2.5, 3)
cut(pipe, c)
pipe.data.materials.append(STEEL)
smooth(pipe)
for ex in (-PIPE_LEN / 2, PIPE_LEN / 2):  # end caps (back half discs)
    bpy.ops.mesh.primitive_cylinder_add(radius=PIPE_R, depth=0.1, vertices=96, location=(ex, 0, 0),
                                        rotation=(0, math.pi / 2, 0))
    cap = bpy.context.object
    bpy.ops.mesh.primitive_cube_add(location=(ex, -2.5, 0))
    cc = bpy.context.object
    cc.scale = (0.5, 2.5, 3)
    cut(cap, cc)
    cap.data.materials.append(STEEL_DARK)
    cap.parent = pipe

FLOOR_Z = -PIPE_R * 0.6
box("floor", (0, 0.75, FLOOR_Z), (PIPE_LEN - 0.3, 1.5, 0.12), WOOD, parent=pipe)
for k in range(12):  # floor plank lines
    box(f"plank{k}", (-PIPE_LEN / 2 + 0.5 + k * 0.72, 0.75, FLOOR_Z + 0.061), (0.02, 1.5, 0.005), STAFF, parent=pipe)
furniture = []
rug = cyl("rug", (0, 0.7, FLOOR_Z + 0.07), 0.9, 0.02, RUG, parent=pipe)
rug.scale = (1.4, 0.5, 1)
furniture.append(rug)
# bunk bed (right)
bed = bpy.data.objects.new("bunk", None)
bpy.context.collection.objects.link(bed)
bed.parent = pipe
bed.location = (2.9, 0.8, FLOOR_Z)
for lvl in range(2):
    zz = 0.35 + lvl * 0.85
    box(f"bedframe{lvl}", (0, 0, zz), (1.9, 0.9, 0.1), STAFF, parent=bed)
    box(f"mattress{lvl}", (0, 0, zz + 0.1), (1.8, 0.8, 0.14), BLANKETS[lvl], bevel=0.04, parent=bed)
    box(f"pillow{lvl}", (0.7, 0, zz + 0.22), (0.35, 0.6, 0.12), PILLOW, bevel=0.05, parent=bed)
for px in (-0.93, 0.93):
    for py in (-0.43, 0.43):
        box("post", (px, py, 0.65), (0.07, 0.07, 1.3), STAFF, parent=bed)
for k in range(4):
    box(f"rung{k}", (-0.93, -0.43, 0.25 + k * 0.28), (0.07, 0.25, 0.04), STAFF, parent=bed)
furniture.append(bed)
# shelves with food and water (left)
shelf = bpy.data.objects.new("shelf", None)
bpy.context.collection.objects.link(shelf)
shelf.parent = pipe
shelf.location = (-2.75, 1.05, FLOOR_Z)
for lvl in range(3):
    box(f"board{lvl}", (0, 0, 0.3 + lvl * 0.45), (1.3, 0.4, 0.05), WOOD, parent=shelf)
    for k in range(5):
        if lvl == 2 and k > 2:
            break
        cyl(f"can{lvl}{k}", (-0.5 + k * 0.25, 0, 0.42 + lvl * 0.45), 0.09, 0.2, CANS[(k + lvl) % 3], parent=shelf)
for px in (-0.63, 0.63):
    box("side", (px, 0, 0.7), (0.05, 0.4, 1.4), WOOD, parent=shelf)
for k in range(3):
    box(f"jug{k}", (-0.4 + k * 0.4, -0.05, 0.12), (0.3, 0.3, 0.26), WATER, bevel=0.05, parent=shelf)
furniture.append(shelf)
# little table with a board game (back middle)
table = bpy.data.objects.new("table", None)
bpy.context.collection.objects.link(table)
table.parent = pipe
table.location = (0.2, 1.2, FLOOR_Z)
cyl("tabletop", (0, 0, 0.55), 0.45, 0.06, WOOD, parent=table)
cyl("tableleg", (0, 0, 0.27), 0.06, 0.55, STAFF, parent=table)
box("game", (0, 0, 0.6), (0.4, 0.4, 0.02), BOARD, parent=table)
furniture.append(table)
# lamp on a cable
cyl("cable", (0, 0.75, PIPE_R - 0.35), 0.015, 0.5, STEEL_DARK, parent=pipe)
sphere("bulb", (0, 0.75, PIPE_R - 0.65), 0.14, LAMP, parent=pipe)
bpy.ops.object.light_add(type="POINT", location=(0, 0.5, PIPE_R - 0.8))
pl = bpy.context.object
pl.data.energy = 320
pl.data.color = (1, 0.82, 0.6)
pl.data.shadow_soft_size = 0.3
pl.parent = pipe
# entrance shaft with a ladder, and an air vent, both rising to the lawn
shaft = cyl("shaft", (SHAFT_X, 0, PIPE_R + 1.6), 0.5, 3.4, STEEL, verts=64, parent=pipe)
bpy.ops.mesh.primitive_cube_add(location=(SHAFT_X, -1.0, PIPE_R + 1.6))
cc = bpy.context.object
cc.scale = (0.6, 1.0, 1.8)
shell = shaft.modifiers.new("shell", "SOLIDIFY")
shell.thickness = 0.06
bpy.context.view_layer.objects.active = shaft
bpy.ops.object.modifier_apply(modifier="shell")
cut(shaft, cc)
for k in range(9):
    box(f"lrung{k}", (SHAFT_X, 0.25, PIPE_R + 0.1 + k * 0.38), (0.5, 0.05, 0.05), STEEL_DARK, parent=pipe)
for lx in (-0.25, 0.25):
    box("lrail", (SHAFT_X + lx, 0.25, PIPE_R + 1.6), (0.05, 0.05, 3.3), STEEL_DARK, parent=pipe)
hatch = cyl("hatch", (SHAFT_X, 0.25, PIPE_R + 3.32), 0.62, 0.1, STEEL_DARK, verts=48, parent=pipe)
vent = cyl("vent", (VENT_X, 0.15, PIPE_R + 1.9), 0.16, 3.9, STEEL_DARK, verts=24, parent=pipe)
cyl("ventcap", (VENT_X, 0.15, PIPE_R + 3.9), 0.36, 0.12, STEEL_DARK, verts=32, parent=pipe)
cyl("ventcap2", (VENT_X, 0.15, PIPE_R + 3.75), 0.2, 0.25, STEEL_DARK, verts=24, parent=pipe)

# the drop: from the sky into the trench, with a bounce
pipe.location = (0, 0, 12)
pipe.keyframe_insert("location", frame=1)
pipe.location = (0, 0, PIPE_Z - 0.1)
pipe.keyframe_insert("location", frame=36)
pipe.location = (0, 0, PIPE_Z)
pipe.keyframe_insert("location", frame=44)
for k, f in enumerate(furniture):  # furniture pops in once it lands
    pop_in(f, 96 + k * 4, f.scale[0] if f.name != "rug" else 1)
rug.scale = (0.001, 0.001, 0.001)
rug.keyframe_insert("scale", frame=96)
rug.scale = (1.4, 0.5, 1)
rug.keyframe_insert("scale", frame=104)

# backfill rising from the pipe to the lawn, with holes left for the shaft and the vent
fill_ = box("backfill", (0, 0.92, 0.5), (PIPE_LEN + 0.1, 1.82, 1.0), SOIL)
for x, r in ((SHAFT_X, 0.52), (VENT_X, 0.18)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=4, location=(x, 0, 0.5), vertices=48)
    cut(fill_, bpy.context.object)
fill_.location = (0, 0, PIPE_Z + PIPE_R - 0.05)
fill_.scale = (1, 1, 0.001)
fill_.keyframe_insert("scale", frame=50)
fill_.scale = (1, 1, -PIPE_Z - PIPE_R + 0.05)
fill_.keyframe_insert("scale", frame=80)
lid = box("grass_lid", (0, 0.92, 0), (PIPE_LEN + 0.1, 1.82, 0.2), GRASS)
for x, r in ((SHAFT_X, 0.52), (VENT_X, 0.18)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=1, location=(x, 0, 0), vertices=48)
    cut(lid, bpy.context.object)
lid.location = (0, 0, 0.1)
lid.scale = (1, 1, 0.001)
lid.keyframe_insert("scale", frame=79)
lid.scale = (1, 1, 1)
lid.keyframe_insert("scale", frame=84)

# ------------------------------------------------------------------ the yard

HX, HY = 1.2, 5.6
box("house", (HX, HY, 1.5), (5.0, 2.6, 3.0), WALL, bevel=0.03)
verts = [(-2.8, -1.5, 0), (2.8, -1.5, 0), (2.8, 1.5, 0), (-2.8, 1.5, 0), (-2.8, 0, 1.6), (2.8, 0, 1.6)]
faces = [(0, 1, 5, 4), (4, 5, 2, 3), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
me = bpy.data.meshes.new("roof")
me.from_pydata(verts, [], faces)
roof = bpy.data.objects.new("roof", me)
bpy.context.collection.objects.link(roof)
roof.location = (HX, HY, 3.0)
roof.data.materials.append(ROOF)
box("chimney", (HX + 1.6, HY + 0.4, 4.0), (0.5, 0.5, 1.4), BRICK)
box("gutter", (HX, HY - 1.5, 3.0), (5.7, 0.12, 0.1), TRIM)
for r in range(2):
    for cx in (-1.6, -0.6, 2.0, 3.0):
        wx, wz = cx + HX - 0.7, 0.9 + r * 1.3
        box("winframe", (wx, HY - 1.31, wz), (0.72, 0.05, 0.87), TRIM)
        box("win", (wx, HY - 1.34, wz), (0.6, 0.05, 0.75), WINDOW)
        box("sill", (wx, HY - 1.38, wz - 0.42), (0.8, 0.12, 0.06), TRIM)
box("doorframe", (HX, HY - 1.31, 0.62), (0.85, 0.05, 1.3), TRIM)
box("door", (HX, HY - 1.34, 0.6), (0.7, 0.05, 1.2), mat("doorcol", (0.15, 0.3, 0.55)))
sphere("knob", (HX + 0.22, HY - 1.38, 0.6), 0.04, GOLD)
box("step", (HX, HY - 1.6, 0.08), (1.3, 0.5, 0.16), TRIM)
# tree
cyl("trunk", (-5.2, 4.8, 1.3), 0.22, 2.6, BARK, verts=16)
for dx, dz, r in ((0, 3.0, 1.2), (-0.6, 2.6, 0.9), (0.7, 2.7, 0.9), (0.1, 3.7, 0.8)):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=3, location=(-5.2 + dx, 4.8, dz))
    lf = bpy.context.object
    lf.data.materials.append(LEAF)
    smooth(lf)
# bushes with flowers along the house
for k in range(5):
    bx = HX - 2.2 + k * 1.1
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.38, subdivisions=2, location=(bx, HY - 1.75, 0.3))
    bu = bpy.context.object
    bu.scale = (1.2, 0.9, 0.9)
    bu.data.materials.append(LEAF)
    smooth(bu)
    for j in range(3):
        sphere("flower", (bx + rng.uniform(-0.3, 0.3), HY - 2.05, 0.35 + rng.uniform(-0.1, 0.25)), 0.06,
               FLOWER[(k + j) % 3], seg=12)
# picket fence across the back of the yard
for k in range(44):
    x = -11 + k * 0.5
    if -1.6 < x - HX < 1.6:
        continue
    box("picket", (x, 8.2, 0.55), (0.14, 0.06, 1.1), TRIM)
for z in (0.35, 0.8):
    box("fence_rail", (0, 8.25, z), (22, 0.05, 0.08), TRIM)
# grass tufts
for k in range(140):
    x, y = rng.uniform(-9, 9), rng.uniform(0.3, 7.8)
    if -4.6 < x < 4.6 and y < 2.0:
        continue
    bpy.ops.mesh.primitive_cone_add(radius1=0.05, radius2=0, depth=rng.uniform(0.15, 0.3), location=(x, y, 0.3),
                                    vertices=5)
    bpy.context.object.data.materials.append(LEAF)

# ------------------------------------------------------------------ wizards


def wizard(name, x, robe, pop, wave):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    P = dict(parent=root)
    bpy.ops.mesh.primitive_cone_add(radius1=0.42, radius2=0.14, depth=1.05, location=(0, 0, 0.53), vertices=48)
    body = bpy.context.object
    body.data.materials.append(robe)
    smooth(body)
    body.parent = root
    bpy.ops.mesh.primitive_torus_add(major_radius=0.27, minor_radius=0.035, location=(0, 0, 0.62))
    belt = bpy.context.object
    belt.data.materials.append(GOLD)
    belt.parent = root
    for k in range(6):  # stars on the robe
        a = -1.2 + k * 0.45
        hgt = 0.25 + (k % 3) * 0.2
        rr = 0.42 - hgt * 0.27
        sphere("star", (math.sin(a) * rr, -math.cos(a) * rr, hgt), 0.035, STAR, seg=10, **P)
    sphere("head", (0, 0, 1.24), 0.24, SKIN, **P)
    for ex in (-0.08, 0.08):
        sphere("eye", (ex, -0.215, 1.29), 0.032, EYE, seg=12, **P)
    sphere("nose", (0, -0.25, 1.22), 0.05, SKIN, seg=12, **P)
    bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.0, depth=0.55, location=(0, -0.13, 0.98),
                                    rotation=(math.pi - 0.25, 0, 0), vertices=32)
    beard = bpy.context.object
    beard.data.materials.append(BEARD)
    smooth(beard)
    beard.parent = root
    cyl("brim", (0, 0, 1.43), 0.4, 0.04, robe, verts=48, **P)
    cyl("band", (0, 0, 1.48), 0.26, 0.07, GOLD, verts=48, **P)
    bpy.ops.mesh.primitive_cone_add(radius1=0.26, radius2=0.08, depth=0.6, location=(0, 0, 1.75), vertices=48)
    hat = bpy.context.object
    hat.data.materials.append(robe)
    smooth(hat)
    hat.parent = root
    bpy.ops.mesh.primitive_cone_add(radius1=0.08, radius2=0.0, depth=0.35, location=(0.1, 0, 2.1),
                                    rotation=(0, math.radians(-40), 0), vertices=24)
    tip = bpy.context.object
    tip.data.materials.append(robe)
    smooth(tip)
    tip.parent = root
    sphere("hatstar", (0.0, -0.2, 1.75), 0.04, STAR, seg=12, **P)
    # arms: a pivot at each shoulder so the staff arm can wave
    arms = []
    for side in (-1, 1):
        piv = bpy.data.objects.new(f"{name}_shoulder", None)
        bpy.context.collection.objects.link(piv)
        piv.parent = root
        piv.location = (side * 0.2, 0, 1.0)
        cyl("sleeve", (side * 0.12, -0.05, -0.18), 0.075, 0.42, robe, rot=(0, side * 0.6, 0), verts=16, parent=piv)
        sphere("hand", (side * 0.24, -0.08, -0.36), 0.07, SKIN, seg=12, parent=piv)
        arms.append(piv)
    staff_arm = arms[1]
    cyl("staff", (0.26, -0.12, -0.05), 0.03, 1.7, STAFF, verts=12, parent=staff_arm)
    sphere("orb", (0.26, -0.12, 0.85), 0.11, ORB, parent=staff_arm)
    bpy.ops.object.light_add(type="POINT", location=(0.26, -0.3, 0.85))
    glow = bpy.context.object
    glow.data.energy = 18
    glow.data.color = (0.55, 0.85, 1.0)
    glow.parent = staff_arm
    root.location = (x, 0.65, FLOOR_Z + PIPE_Z + 0.07)
    pop_in(root, pop)
    root.rotation_euler = (0, 0, math.radians(-12))
    root.keyframe_insert("rotation_euler", frame=pop + 10)
    root.rotation_euler = (0, 0, math.radians(12))
    root.keyframe_insert("rotation_euler", frame=FRAMES)
    for f, ang in ((pop + 10, 0), (wave, -1.0), (wave + 8, -0.6), (wave + 16, -1.1), (wave + 24, -0.4)):
        staff_arm.rotation_euler = (0, ang, 0)
        staff_arm.keyframe_insert("rotation_euler", frame=f)
    return root


for i, (x, pop) in enumerate(((-1.5, 104), (0.2, 112), (1.7, 120))):
    wizard(f"wizard{i}", x, ROBES[i], pop, pop + 14)

# ------------------------------------------------------------------ light, sky, camera

world = bpy.data.worlds.new("sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
grad = wn.nodes.new("ShaderNodeTexGradient")
mapping = wn.nodes.new("ShaderNodeMapping")
coord = wn.nodes.new("ShaderNodeTexCoord")
mapping.inputs["Rotation"].default_value = (0, math.pi / 2, 0)
ramp = wn.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.78, 0.9, 1.0, 1)
ramp.color_ramp.elements[1].color = (0.22, 0.52, 0.92, 1)
wn.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
wn.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
wn.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
wn.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9

bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(12), math.radians(32)))
sun = bpy.context.object
sun.data.energy = 3.2
sun.data.angle = math.radians(3)
sun.data.color = (1.0, 0.95, 0.87)
bpy.ops.object.light_add(type="AREA", location=(0, -9, -2.5), rotation=(math.radians(90), 0, 0))
fillv = bpy.context.object
fillv.data.energy = 550
fillv.data.size = 12

bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 32
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 5.6


def aim(at):
    d = Vector(at) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


for frame, loc, at in ((1, (4.5, -17.0, 3.4), (0, 2.0, -2.0)), (FRAMES, (5.0, -11.5, 0.6), (0.3, 1.0, -3.0))):
    cam.location = loc
    aim(at)
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)
focus = bpy.data.objects.new("focus", None)
bpy.context.collection.objects.link(focus)
focus.location = (0.2, 0.7, -3.4)
cam.data.dof.focus_object = focus

# finish: a soft glow around bright lights (lamp, staff orbs) and a gentle vignette
scene.use_nodes = True
ct = scene.node_tree
rl = ct.nodes["Render Layers"]
comp = ct.nodes["Composite"]
glare = ct.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 0.9
glare.size = 7
glare.mix = -0.6
ell = ct.nodes.new("CompositorNodeEllipseMask")
ell.width, ell.height = 0.95, 0.75
blur = ct.nodes.new("CompositorNodeBlur")
blur.size_x = blur.size_y = 220
mixv = ct.nodes.new("CompositorNodeMixRGB")
mixv.blend_type = "MULTIPLY"
mixv.inputs[0].default_value = 0.35
ct.links.new(rl.outputs["Image"], glare.inputs["Image"])
ct.links.new(ell.outputs["Mask"], blur.inputs["Image"])
ct.links.new(glare.outputs["Image"], mixv.inputs[1])
ct.links.new(blur.outputs["Image"], mixv.inputs[2])
ct.links.new(mixv.outputs["Image"], comp.inputs["Image"])

OUT.mkdir(parents=True, exist_ok=True)
if STILL:
    scene.frame_set(STILL)
    scene.render.filepath = str(OUT / f"still_{STILL:03d}.png")
    bpy.ops.render.render(write_still=True)
else:
    scene.frame_start, scene.frame_end = START, END or FRAMES  # a slice, so several machines share the work
    scene.render.filepath = str(OUT / "f_")
    bpy.ops.render.render(animation=True)
print("done")
