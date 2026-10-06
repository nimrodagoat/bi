"""Minecraft-style first-person parkour footage, made from scratch.

Each video gets its own random course of floating blocks, and the camera
sprints and jumps along it. Every texture is generated here (nothing comes from
Minecraft itself), so the footage is original and free to use. Rendering uses
OpenGL on the CPU (Mesa llvmpipe through moderngl), so no graphics card is needed.
"""

from __future__ import annotations

import math
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

T = 16  # texture size in pixels
RUN_SPEED = 5.6  # blocks per second while sprinting
JUMP_SPEED = 6.2  # horizontal blocks per second while jumping
EYE = 1.62  # eye height above the block top


# ── Textures ────────────────────────────────────────────────────────────────


def _noise(rng, base, amp):
    tile = np.array(base, dtype=np.int16)[None, None, :] + rng.integers(-amp, amp + 1, (T, T, 1))
    return tile


def _border(tile, color, width=1):
    c = np.array(color, dtype=np.int16)
    tile[:width, :] = c
    tile[-width:, :] = c
    tile[:, :width] = c
    tile[:, -width:] = c
    return tile


def _specks(rng, tile, color, share):
    mask = rng.random((T, T)) < share
    tile[mask] = color
    return tile


def make_textures(rng) -> dict[str, np.ndarray]:
    tex: dict[str, np.ndarray] = {}
    dirt = _specks(rng, _noise(rng, (134, 96, 67), 14), (104, 72, 48), 0.12)
    tex["dirt"] = dirt
    tex["grass_top"] = _specks(rng, _noise(rng, (98, 163, 54), 16), (76, 130, 40), 0.15)
    side = dirt.copy()
    top = _noise(rng, (98, 163, 54), 14)
    side[:3] = top[:3]
    drip = rng.random(T) < 0.5
    side[3, drip] = top[3, drip]
    tex["grass_side"] = side
    stone = _noise(rng, (127, 127, 127), 12)
    stone = _specks(rng, stone, (102, 102, 102), 0.18)
    tex["stone"] = stone
    planks = _noise(rng, (164, 132, 80), 8)
    for row in range(T):
        if row % 4 == 3:
            planks[row] = (112, 86, 52)
        seam = 0 if (row // 4) % 2 == 0 else 8
        planks[row, seam] = (126, 98, 60)
    tex["planks"] = planks
    log = _noise(rng, (104, 82, 52), 10)
    for col in range(0, T, 3):
        log[:, col] = (80, 62, 38)
    tex["log_side"] = log
    ring = _noise(rng, (176, 142, 88), 6)
    yy, xx = np.mgrid[0:T, 0:T]
    r = np.hypot(yy - 7.5, xx - 7.5)
    ring[(r.astype(int) % 3) == 0] = (140, 108, 64)
    ring[r > 7] = (104, 82, 52)
    tex["log_top"] = ring
    leaves = _noise(rng, (62, 128, 42), 22)
    tex["leaves"] = _specks(rng, leaves, (38, 86, 26), 0.25)
    for name, base, edge in [
        ("gold", (248, 214, 76), (214, 166, 34)),
        ("diamond", (104, 222, 214), (54, 166, 160)),
        ("emerald", (64, 206, 104), (28, 150, 64)),
        ("quartz", (236, 231, 224), (212, 205, 196)),
    ]:
        tile = _noise(rng, base, 8)
        tile[2:5, 2:5] = np.minimum(np.array(base) + 30, 255)
        tex[name] = _border(tile, edge)
    for name, base in [
        ("red_wool", (176, 46, 38)), ("orange_wool", (240, 118, 20)),
        ("yellow_wool", (248, 198, 39)), ("lime_wool", (112, 185, 25)),
        ("cyan_wool", (21, 137, 145)), ("blue_wool", (53, 57, 157)),
        ("purple_wool", (121, 42, 172)), ("magenta_wool", (189, 68, 179)),
        ("white_wool", (234, 236, 236)),
    ]:
        tile = _noise(rng, base, 7)
        tile[(yy + xx) % 2 == 0] += 6
        tex[name] = tile
    tex["cloud"] = np.full((T, T, 3), 255, dtype=np.int16)
    return {k: np.clip(v, 0, 255).astype(np.uint8) for k, v in tex.items()}


# (top, side, bottom) texture of every block type
BLOCKS = {
    "grass": ("grass_top", "grass_side", "dirt"),
    "dirt": ("dirt", "dirt", "dirt"),
    "stone": ("stone", "stone", "stone"),
    "planks": ("planks", "planks", "planks"),
    "log": ("log_top", "log_side", "log_top"),
    "leaves": ("leaves", "leaves", "leaves"),
    "gold": ("gold", "gold", "gold"),
    "diamond": ("diamond", "diamond", "diamond"),
    "emerald": ("emerald", "emerald", "emerald"),
    "quartz": ("quartz", "quartz", "quartz"),
    "cloud": ("cloud", "cloud", "cloud"),
    **{w: (w, w, w) for w in (
        "red_wool", "orange_wool", "yellow_wool", "lime_wool", "cyan_wool",
        "blue_wool", "purple_wool", "magenta_wool", "white_wool",
    )},
}

THEMES = [
    ["red_wool", "orange_wool", "yellow_wool", "lime_wool", "cyan_wool", "blue_wool", "purple_wool", "magenta_wool"],
    ["gold", "diamond", "emerald"],
    ["quartz", "white_wool"],
    ["planks", "log"],
    ["stone", "grass"],
]


# ── Course ──────────────────────────────────────────────────────────────────


@dataclass
class Block:
    x: int
    y: int
    z: int
    kind: str
    flat: bool = False  # no face shading (clouds)


def build_course(rng: random.Random, jumps: int) -> tuple[list[Block], list[np.ndarray]]:
    """Return all blocks in the world and the block-top centres the runner lands on."""
    blocks: list[Block] = []
    path: list[np.ndarray] = []
    headings = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    h = 0
    x = y = z = 0
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            blocks.append(Block(dx, -1, dz, "grass"))
    path.append(np.array([0.5, 0.0, 0.5]))
    theme = rng.choice(THEMES)
    since_turn = 0
    for i in range(jumps):
        if i % 8 == 7:
            theme = rng.choice(THEMES)
        if since_turn > 6 and rng.random() < 0.18:
            h = (h + rng.choice((1, 3))) % 4
            since_turn = 0
        fx, fz = headings[h]
        sx, sz = fz, -fx  # sideways
        dist = rng.choice((2, 3, 3, 4))
        dy = rng.choice((-1, 0, 0, 0, 1))
        if dist == 4 and dy > 0:
            dy = 0
        side = rng.choice((-1, 0, 0, 1))
        x, y, z = x + fx * dist + sx * side, y + dy, z + fz * dist + sz * side
        kind = rng.choice(theme)
        blocks.append(Block(x, y - 1, z, kind))
        path.append(np.array([x + 0.5, float(y), z + 0.5]))
        if rng.random() < 0.15:  # a short runway: land, run, keep going
            for _ in range(rng.choice((1, 2))):
                x, z = x + fx, z + fz
                blocks.append(Block(x, y - 1, z, kind))
                path.append(np.array([x + 0.5, float(y), z + 0.5]))
        since_turn += 1
    return blocks, path


def add_scenery(rng: random.Random, blocks: list[Block], path: list[np.ndarray]) -> None:
    """Floating islands (some with trees) beside the course, and clouds above."""
    pts = np.array(path)
    for anchor in path[::5]:
        for _ in range(2):
            ang = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(14, 34)
            cx = int(anchor[0] + math.cos(ang) * dist)
            cz = int(anchor[2] + math.sin(ang) * dist)
            cy = int(anchor[1] + rng.uniform(-14, 6))
            radius = rng.uniform(2.0, 4.5)
            # Keep the runner's way clear: no island near any part of the course.
            if np.min(np.hypot(pts[:, 0] - cx, pts[:, 2] - cz)) < radius + 7:
                continue
            r = int(radius) + 1
            for ix in range(-r, r + 1):
                for iz in range(-r, r + 1):
                    d = math.hypot(ix, iz)
                    if d > radius:
                        continue
                    depth = max(1, int((radius - d) * 1.6 + rng.random()))
                    for k in range(depth):
                        kind = "grass" if k == 0 else ("dirt" if k < 3 else "stone")
                        blocks.append(Block(cx + ix, cy - k, cz + iz, kind))
            if rng.random() < 0.6:
                trunk = rng.choice((3, 4, 5))
                for k in range(1, trunk + 1):
                    blocks.append(Block(cx, cy + k, cz, "log"))
                for ly in range(trunk - 1, trunk + 2):
                    reach = 1 if ly == trunk + 1 else 2
                    for lx in range(-reach, reach + 1):
                        for lz in range(-reach, reach + 1):
                            trunk_here = (lx, lz) == (0, 0) and ly <= trunk
                            if abs(lx) + abs(lz) <= reach + 1 and not trunk_here:
                                blocks.append(Block(cx + lx, cy + ly, cz + lz, "leaves"))
    lo = np.min(path, axis=0)
    hi = np.max(path, axis=0)
    for _ in range(int((hi[0] - lo[0] + hi[2] - lo[2]) / 6) + 10):
        cx = int(rng.uniform(lo[0] - 60, hi[0] + 60))
        cz = int(rng.uniform(lo[2] - 60, hi[2] + 60))
        cy = int(hi[1] + 22)
        w, d = rng.randint(4, 12), rng.randint(3, 9)
        for ix in range(w):
            for iz in range(d):
                if rng.random() < 0.88:
                    blocks.append(Block(cx + ix, cy, cz + iz, "cloud", flat=True))


# ── Runner (camera path) ────────────────────────────────────────────────────


class Runner:
    """Where the eyes are at any time: sprint across each block, jump to the next."""

    def __init__(self, path: list[np.ndarray]):
        self.segments: list[tuple[float, float, np.ndarray, np.ndarray, float]] = []
        t = 0.0
        prev_land = path[0].copy()
        for a, b in zip(path, path[1:]):
            step = b - a
            flat = math.hypot(step[0], step[2])
            direction = np.array([step[0], 0.0, step[2]]) / max(flat, 1e-6)
            if flat <= 1.01 and abs(step[1]) < 0.01:  # neighbouring block: just run
                dur = flat / RUN_SPEED
                self.segments.append((t, t + dur, prev_land, b.copy(), 0.0))
                t += dur
                prev_land = b.copy()
                continue
            takeoff = a + direction * 0.3
            land = b - direction * 0.3
            run = np.linalg.norm(takeoff - prev_land) / RUN_SPEED
            self.segments.append((t, t + run, prev_land, takeoff, 0.0))
            t += run
            dur = max(0.38, np.linalg.norm((land - takeoff)[[0, 2]]) / JUMP_SPEED)
            self.segments.append((t, t + dur, takeoff, land, 1.15 + max(0.0, step[1]) * 0.35))
            t += dur
            prev_land = land
        self.duration = t

    def feet(self, t: float) -> tuple[np.ndarray, bool]:
        for t0, t1, p0, p1, height in self.segments:
            if t <= t1:
                u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
                pos = p0 + (p1 - p0) * u
                pos[1] += 4 * height * u * (1 - u)
                return pos, height == 0.0
        return self.segments[-1][3].copy(), True


def _look_at(eye, forward):
    f = forward / np.linalg.norm(forward)
    r = np.cross(f, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    m = np.identity(4)
    m[0, :3], m[1, :3], m[2, :3] = r, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def _perspective(fovy, aspect, near, far):
    f = 1 / math.tan(math.radians(fovy) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


# ── Rendering ───────────────────────────────────────────────────────────────

VERTEX = """
#version 330
uniform mat4 mvp;
uniform vec3 cam;
uniform float tiles;
in vec3 in_pos; in vec2 in_uv; in float in_face;
in vec3 i_off; in vec3 i_tiles; in float i_flat;
out vec2 v_uv; out float v_shade; out float v_dist;
void main() {
    vec3 world = in_pos + i_off;
    gl_Position = mvp * vec4(world, 1.0);
    float tile = in_face < 0.5 ? i_tiles.x : (in_face < 1.5 ? i_tiles.z : i_tiles.y);
    v_uv = vec2((tile + 0.002 + in_uv.x * 0.996) / tiles, 0.002 + in_uv.y * 0.996);
    float shade = in_face < 0.5 ? 1.0 : (in_face < 1.5 ? 0.55 : (in_face < 3.5 ? 0.82 : 0.68));
    v_shade = mix(shade, 1.0, i_flat);
    v_dist = length(world - cam);
}
"""

FRAGMENT = """
#version 330
uniform sampler2D tex;
uniform vec3 fog_color;
in vec2 v_uv; in float v_shade; in float v_dist;
out vec4 color;
void main() {
    vec3 c = texture(tex, v_uv).rgb * v_shade;
    float fog = clamp((v_dist - 45.0) / 70.0, 0.0, 0.85);
    color = vec4(mix(c, fog_color, fog), 1.0);
}
"""

SKY_VERTEX = """
#version 330
in vec2 in_pos; out vec2 v_pos;
void main() { v_pos = in_pos; gl_Position = vec4(in_pos, 0.9999, 1.0); }
"""

SKY_FRAGMENT = """
#version 330
uniform mat4 inv_vp; uniform vec3 sun;
in vec2 v_pos; out vec4 color;
void main() {
    vec4 far = inv_vp * vec4(v_pos, 1.0, 1.0);
    vec4 near = inv_vp * vec4(v_pos, -1.0, 1.0);
    vec3 ray = normalize(far.xyz / far.w - near.xyz / near.w);
    vec3 horizon = vec3(0.75, 0.85, 1.0), zenith = vec3(0.47, 0.65, 1.0), below = vec3(0.30, 0.42, 0.78);
    vec3 c = ray.y > 0.0 ? mix(horizon, zenith, smoothstep(0.0, 0.6, ray.y))
                         : mix(horizon, below, smoothstep(0.0, 0.35, -ray.y));
    vec3 side = normalize(cross(sun, vec3(0.0, 1.0, 0.0)));
    vec3 up = cross(side, sun);
    if (dot(ray, sun) > 0.0) {
        vec2 p = vec2(dot(ray, side), dot(ray, up)) / dot(ray, sun);
        if (max(abs(p.x), abs(p.y)) < 0.07) c = vec3(1.0, 0.98, 0.85);
    }
    color = vec4(c, 1.0);
}
"""


def _cube() -> np.ndarray:
    """36 vertices: position, uv, face (0 top, 1 bottom, 2/3 ±x, 4/5 ±z)."""
    faces = [
        (0, [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)]),
        (1, [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
        (2, [(1, 1, 0), (1, 1, 1), (1, 0, 1), (1, 0, 0)]),
        (3, [(0, 1, 1), (0, 1, 0), (0, 0, 0), (0, 0, 1)]),
        (4, [(1, 1, 1), (0, 1, 1), (0, 0, 1), (1, 0, 1)]),
        (5, [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)]),
    ]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]  # v=0 is the top row of the texture
    data = []
    for face, corners in faces:
        for i in (0, 1, 2, 0, 2, 3):
            data.append([*corners[i], *uvs[i], face])
    return np.array(data, dtype="f4")


def render(out: Path, duration: float, cfg: dict, seed: str = "") -> Path:
    """Render `duration` seconds of parkour to `out` (vertical, H.264)."""
    import moderngl

    v = cfg.get("video", {})
    w, h, fps = v.get("width", 1080), v.get("height", 1920), v.get("fps", 30)
    scale = cfg.get("visuals", {}).get("parkour_render_scale", 0.75)
    rw, rh = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2
    rng = random.Random(f"parkour-{seed}")
    nrng = np.random.default_rng(rng.randrange(2**32))

    # Build the world, with enough course for the whole video.
    jumps = int(duration * 1.6) + 12
    blocks, path = build_course(rng, jumps)
    runner = Runner(path)
    while runner.duration < duration + 1:
        jumps += 10
        blocks, path = build_course(random.Random(f"parkour-{seed}"), jumps)
        runner = Runner(path)
    add_scenery(rng, blocks, path)

    textures = make_textures(nrng)
    names = list(textures)
    atlas = np.concatenate([textures[n] for n in names], axis=1)
    index = {n: i for i, n in enumerate(names)}
    inst = np.array(
        [
            [b.x, b.y, b.z, index[BLOCKS[b.kind][0]], index[BLOCKS[b.kind][1]], index[BLOCKS[b.kind][2]], float(b.flat)]
            for b in blocks
        ],
        dtype="f4",
    )

    ctx = moderngl.create_standalone_context(backend="egl")
    prog = ctx.program(vertex_shader=VERTEX, fragment_shader=FRAGMENT)
    sky = ctx.program(vertex_shader=SKY_VERTEX, fragment_shader=SKY_FRAGMENT)
    tex = ctx.texture((atlas.shape[1], atlas.shape[0]), 3, atlas.tobytes())
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    prog["tiles"].value = float(len(names))
    prog["fog_color"].value = (0.75, 0.85, 1.0)
    vao = ctx.vertex_array(
        prog,
        [
            (ctx.buffer(_cube().tobytes()), "3f 2f 1f", "in_pos", "in_uv", "in_face"),
            (ctx.buffer(inst.tobytes()), "3f 3f 1f/i", "i_off", "i_tiles", "i_flat"),
        ],
    )
    quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
    sky_vao = ctx.vertex_array(sky, [(quad, "2f", "in_pos")])
    sun = np.array([0.35, 0.55, 0.75])
    sky["sun"].value = tuple(sun / np.linalg.norm(sun))

    msaa = ctx.framebuffer(
        color_attachments=[ctx.renderbuffer((rw, rh), samples=4)],
        depth_attachment=ctx.depth_renderbuffer((rw, rh), samples=4),
    )
    plain = ctx.simple_framebuffer((rw, rh))
    proj = _perspective(cfg.get("visuals", {}).get("parkour_fov", 96), rw / rh, 0.05, 220.0)

    out.parent.mkdir(parents=True, exist_ok=True)
    cross = f"drawbox=x=iw/2-2:y=ih/2-16:w=4:h=32:color=white@0.85:t=fill,drawbox=x=iw/2-16:y=ih/2-2:w=32:h=4:color=white@0.85:t=fill"
    enc = subprocess.Popen(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{rw}x{rh}", "-r", str(fps), "-i", "-",
            "-vf", f"vflip,scale={w}:{h}:flags=bicubic,{cross}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out),
        ],
        stdin=subprocess.PIPE,
    )

    yaw = pitch = None
    frames = int(duration * fps) + 1
    try:
        for i in range(frames):
            t = i / fps
            feet, grounded = runner.feet(t)
            ahead, _ = runner.feet(t + 0.55)
            target, _ = runner.feet(t + 1.0)
            eye = feet + [0.0, EYE, 0.0]
            if grounded:
                eye[1] += 0.04 * math.sin(t * RUN_SPEED * math.pi)
            d = ahead - feet
            want_yaw = math.atan2(d[0], d[2]) if math.hypot(d[0], d[2]) > 1e-3 else (yaw or 0.0)
            look = target - eye
            want_pitch = max(-0.62, min(-0.12, math.atan2(look[1], math.hypot(look[0], look[2]))))
            if yaw is None:
                yaw, pitch = want_yaw, want_pitch
            dyaw = (want_yaw - yaw + math.pi) % (2 * math.pi) - math.pi
            yaw += dyaw * min(1.0, 7.0 / fps)
            pitch += (want_pitch - pitch) * min(1.0, 5.0 / fps)
            forward = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
            vp = proj @ _look_at(eye, forward)

            msaa.use()
            ctx.clear(0.75, 0.85, 1.0, depth=1.0)
            ctx.disable(moderngl.DEPTH_TEST)
            sky["inv_vp"].write(np.linalg.inv(vp).T.astype("f4").tobytes())
            sky_vao.render(moderngl.TRIANGLE_STRIP)
            ctx.enable(moderngl.DEPTH_TEST)
            prog["mvp"].write(vp.T.astype("f4").tobytes())
            prog["cam"].value = tuple(eye)
            tex.use()
            vao.render(instances=len(inst))
            ctx.copy_framebuffer(plain, msaa)
            enc.stdin.write(plain.read(components=3))
    finally:
        enc.stdin.close()
        enc.wait()
        ctx.release()
    if enc.returncode != 0:
        raise RuntimeError("ffmpeg failed while encoding parkour footage")
    return out
