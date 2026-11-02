"""5-second 3D test: a back-yard diorama cut open, a steel-pipe bunker dropping
into its hole and three toy wizards popping in. Run with Blender's Python (bpy):
python bunker3d.py OUT_DIR [--still FRAME] [--samples N]"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[1:]
OUT = Path(args[0])
STILL = int(args[args.index("--still") + 1]) if "--still" in args else None
SAMPLES = int(args[args.index("--samples") + 1]) if "--samples" in args else 24
SCALE = int(args[args.index("--scale") + 1]) if "--scale" in args else 100
START = int(args[args.index("--start") + 1]) if "--start" in args else 1
END = int(args[args.index("--end") + 1]) if "--end" in args else None
FPS, FRAMES = 30, 150

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = SCALE
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = 0.0


# ------------------------------------------------------------------ helpers

def mat(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, noise=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if noise:  # mottled colour (soil, grass)
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise[0]
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*noise[1], 1)
        ramp.color_ramp.elements[1].color = (*color, 1)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def corrugated(name, color):
    m = mat(name, color, rough=0.35, metal=0.85)
    nt = m.node_tree
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 18
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


def box(name, loc, size, material, bevel=0.0):
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
    return o


def cut(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


# ------------------------------------------------------------------ materials

GRASS = mat("grass", (0.18, 0.55, 0.12), noise=(40, (0.12, 0.42, 0.08)))
SOIL = mat("soil", (0.36, 0.22, 0.12), rough=0.9, noise=(6, (0.22, 0.13, 0.07)))
SOIL_DEEP = mat("soil_deep", (0.25, 0.15, 0.08), rough=0.95, noise=(9, (0.15, 0.09, 0.05)))
STEEL = corrugated("steel", (0.62, 0.65, 0.68))
WOOD = mat("wood", (0.55, 0.33, 0.16), rough=0.7, noise=(30, (0.42, 0.24, 0.11)))
WALL = mat("wall", (0.85, 0.82, 0.74))
ROOF = mat("roof", (0.68, 0.24, 0.16))
WINDOW = mat("window", (0.12, 0.25, 0.42), rough=0.15)
SKIN = mat("skin", (0.95, 0.94, 0.92), rough=0.5)
BEARD = mat("beard", (0.97, 0.97, 0.97), rough=0.9)
STAFF = mat("staff", (0.35, 0.2, 0.1))
ORB = mat("orb", (0.6, 0.85, 1.0), emit=(0.55, 0.85, 1.0), strength=8)
LAMP = mat("lamp", (1, 0.9, 0.7), emit=(1, 0.85, 0.6), strength=12)
ROBES = [mat("robe1", (0.33, 0.2, 0.62)), mat("robe2", (0.15, 0.42, 0.62)), mat("robe3", (0.55, 0.16, 0.3))]
GOLD = mat("gold", (1.0, 0.78, 0.2), rough=0.3, metal=1.0)

# ------------------------------------------------------------------ the diorama (cut face at y = 0)

W_, D_, H_ = 40.0, 30.0, 16.0          # width, depth, soil height; the lawn is at z = 0
soil = box("soil", (0, D_ / 2, -H_ / 2), (W_, D_, H_), SOIL)
lawn = box("lawn", (0, D_ / 2, 0.1), (W_ + 0.04, D_ + 0.04, 0.2), GRASS)
for i, (x, z, r) in enumerate(((-4.6, -1.4, 0.35), (4.2, -6.6, 0.5), (-3.4, -8.8, 0.45), (2.6, -9.6, 0.3),
                               (-5.2, -5.4, 0.3), (5.0, -2.2, 0.25), (0.6, -7.4, 0.28))):  # stones in the cut
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=2, location=(x, 0.05, z))
    st = bpy.context.object
    st.scale = (1.3, 0.6, 0.8)
    st.data.materials.append(SOIL_DEEP)

PIPE_R, PIPE_Z, PIPE_LEN = 1.6, -3.4, 9.0
# the hole the pipe sits in: a cylinder cut through the front face
bpy.ops.mesh.primitive_cylinder_add(radius=PIPE_R + 0.06, depth=PIPE_LEN + 0.1, vertices=96,
                                    location=(0, 0, PIPE_Z), rotation=(0, math.pi / 2, 0))
cut(soil, bpy.context.object)

# an open trench above it, filled back in after the pipe lands
bpy.ops.mesh.primitive_cube_add(location=(0, 0.9, PIPE_Z / 2 + 0.2))
tr = bpy.context.object
tr.scale = ((PIPE_LEN + 0.12) / 2, 0.9, (-PIPE_Z + 0.6) / 2)
bpy.ops.object.transform_apply(scale=True)
cut(soil, tr)
bpy.ops.mesh.primitive_cube_add(location=(0, 0.9, PIPE_Z / 2 + 0.2))
tr = bpy.context.object
tr.scale = ((PIPE_LEN + 0.12) / 2, 0.9, (-PIPE_Z + 0.6) / 2)
bpy.ops.object.transform_apply(scale=True)
cut(lawn, tr)
fill_ = box("backfill", (0, 0.92, 0), (PIPE_LEN + 0.1, 1.82, 1.0), SOIL)  # grows up from the pipe
fill_.data.vertices.foreach_set("co", [c for v in fill_.data.vertices for c in (v.co.x, v.co.y, v.co.z + 0.5)])
fill_.location = (0, 0, PIPE_Z + PIPE_R - 0.05)
fill_.scale = (1, 1, 0.001)
fill_.keyframe_insert("scale", frame=52)
fill_.scale = (1, 1, -PIPE_Z - PIPE_R + 0.05)
fill_.keyframe_insert("scale", frame=80)
grass_lid = box("grass_lid", (0, 0.92, -0.2), (PIPE_LEN + 0.1, 1.82, 0.2), GRASS)
grass_lid.scale = (1, 1, 0.001)
grass_lid.location = (0, 0.92, 0.1)
grass_lid.keyframe_insert("scale", frame=79)
grass_lid.scale = (1, 1, 1)
grass_lid.keyframe_insert("scale", frame=84)

# corrugated pipe; the front half is cut away so we see inside
bpy.ops.mesh.primitive_cylinder_add(radius=PIPE_R, depth=PIPE_LEN, vertices=128, location=(0, 0, 0),
                                    rotation=(0, math.pi / 2, 0))
pipe = bpy.context.object
pipe.name = "pipe"
bpy.ops.object.transform_apply(rotation=True)
solid = pipe.modifiers.new("shell", "SOLIDIFY")
solid.thickness = 0.12
bpy.ops.object.modifier_apply(modifier="shell")
bpy.ops.mesh.primitive_cube_add(location=(0, -2.5, 0))
c = bpy.context.object
c.scale = (PIPE_LEN, 2.5, 3)
cut(pipe, c)
pipe.data.materials.append(STEEL)
smooth(pipe)
floor = box("floor", (0, 0.75, -PIPE_R * 0.6), (PIPE_LEN - 0.3, 1.5, 0.12), WOOD)
floor.parent = pipe
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(0, 0.9, PIPE_R - 0.3))
lamp = bpy.context.object
lamp.data.materials.append(LAMP)
lamp.parent = pipe
bpy.ops.object.light_add(type="POINT", location=(0, 0.5, PIPE_R - 0.6))
pl = bpy.context.object
pl.data.energy = 300
pl.data.color = (1, 0.85, 0.65)
pl.parent = pipe

# the pipe drops from the sky into its hole (frames 1-45), with a little bounce
pipe.location = (0, 0, 10)
pipe.keyframe_insert("location", frame=1)
pipe.location = (0, 0, PIPE_Z - 0.1)
pipe.keyframe_insert("location", frame=38)
pipe.location = (0, 0, PIPE_Z)
pipe.keyframe_insert("location", frame=46)

# ------------------------------------------------------------------ the house behind

HX, HY = 1.2, 5.6
box("house", (HX, HY, 1.5), (5.0, 2.6, 3.0), WALL, bevel=0.03)
verts = [(-2.8, -1.5, 0), (2.8, -1.5, 0), (2.8, 1.5, 0), (-2.8, 1.5, 0), (-2.8, 0, 1.6), (2.8, 0, 1.6)]
faces = [(0, 1, 5, 4), (3, 2, 5, 4)[::-1], (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
me = bpy.data.meshes.new("roof")
me.from_pydata(verts, [], faces)
roof = bpy.data.objects.new("roof", me)
bpy.context.collection.objects.link(roof)
roof.location = (HX, HY, 3.0)
roof.data.materials.append(ROOF)
for r in range(2):
    for cx in (-1.6, -0.6, 2.0, 3.0):
        box(f"win{r}{cx}", (cx + HX - 0.7, HY - 1.32, 0.9 + r * 1.3), (0.6, 0.06, 0.75), WINDOW)
box("door", (HX + 0.0, HY - 1.32, 0.6), (0.7, 0.06, 1.2), WINDOW)

# ------------------------------------------------------------------ wizards

def wizard(name, x, robe, pop):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    parts = []
    bpy.ops.mesh.primitive_cone_add(radius1=0.42, radius2=0.12, depth=1.1, location=(0, 0, 0.55), vertices=32)
    parts.append((bpy.context.object, robe))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.24, location=(0, 0, 1.25))
    parts.append((bpy.context.object, SKIN))
    bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.0, depth=0.5, location=(0, -0.14, 1.0),
                                    rotation=(math.pi, 0, 0), vertices=24)
    parts.append((bpy.context.object, BEARD))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.38, depth=0.05, location=(0, 0, 1.43), vertices=32)
    parts.append((bpy.context.object, robe))
    bpy.ops.mesh.primitive_cone_add(radius1=0.26, radius2=0.0, depth=0.85, location=(0.05, 0, 1.85),
                                    rotation=(0, math.radians(-12), 0), vertices=32)
    parts.append((bpy.context.object, robe))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0.12, -0.2, 1.75))
    parts.append((bpy.context.object, GOLD))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=1.5, location=(0.45, -0.1, 0.75), vertices=12)
    parts.append((bpy.context.object, STAFF))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0.45, -0.1, 1.55))
    parts.append((bpy.context.object, ORB))
    for i, (o, m) in enumerate(parts):
        o.data.materials.append(m)
        smooth(o)
        o.parent = root
    bpy.ops.object.light_add(type="POINT", location=(0.45, -0.25, 1.55))
    glow = bpy.context.object
    glow.data.energy = 15
    glow.data.color = (0.55, 0.85, 1.0)
    glow.parent = root
    root.location = (x, 0.7, PIPE_Z - PIPE_R * 0.6 + 0.06)
    root.scale = (0.001,) * 3
    root.keyframe_insert("scale", frame=pop)
    root.scale = (1.15,) * 3
    root.keyframe_insert("scale", frame=pop + 7)
    root.scale = (1,) * 3
    root.keyframe_insert("scale", frame=pop + 11)
    root.rotation_euler = (0, 0, math.radians(-15))
    root.keyframe_insert("rotation_euler", frame=pop + 11)
    root.rotation_euler = (0, 0, math.radians(15))
    root.keyframe_insert("rotation_euler", frame=FRAMES)
    return root


for i, (x, pop) in enumerate(((-2.0, 92), (0.0, 102), (2.0, 112))):
    wizard(f"wizard{i}", x, ROBES[i], pop)

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
ramp.color_ramp.elements[0].color = (0.75, 0.88, 1.0, 1)
ramp.color_ramp.elements[1].color = (0.25, 0.55, 0.92, 1)
wn.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
wn.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
wn.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
wn.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9

bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), math.radians(10), math.radians(30)))
sun = bpy.context.object
sun.data.energy = 3.0
sun.data.angle = math.radians(4)
bpy.ops.object.light_add(type="AREA", location=(0, -8, -2), rotation=(math.radians(90), 0, 0))
fillv = bpy.context.object
fillv.data.energy = 600
fillv.data.size = 10

bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 30


def aim(at):
    d = Vector(at) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


for frame, loc, at in ((1, (4.5, -17.0, 3.2), (0, 2.0, -2.2)), (FRAMES, (5.5, -11.5, 0.8), (0.3, 1.0, -3.0))):
    cam.location = loc
    aim(at)
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)

OUT.mkdir(parents=True, exist_ok=True)
if STILL:
    scene.frame_set(STILL)
    scene.render.filepath = str(OUT / f"still_{STILL:03d}.png")
    bpy.ops.render.render(write_still=True)
else:
    scene.frame_start, scene.frame_end = START, END or FRAMES  # a slice, so several machines can share the work
    scene.render.filepath = str(OUT / "f_")
    bpy.ops.render.render(animation=True)
print("done")
