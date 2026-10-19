"""Stick figures: the hero ("you") and the creatures, with simple poses.

A pose is a set of limb angles. Angles are measured from straight down, in
radians; positive swings the limb forward (the way the figure faces).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import cairo

from .gfx import eyes, glow, noise, set_color, stroke_line

# limb lengths for scale 1 (pixels)
TORSO, THIGH, SHIN, UPPER, FORE, HEAD = 100, 64, 64, 56, 54, 27


@dataclass
class Pose:
    lean: float = 0.0          # torso, + leans forward
    hip_f: float = 0.08        # front thigh
    knee_f: float = 0.05       # front knee bend (shin swings back)
    hip_b: float = -0.08
    knee_b: float = 0.05
    sh_f: float = 0.12         # front upper arm
    el_f: float = 0.15         # front elbow bend (forearm swings forward/up)
    sh_b: float = -0.12
    el_b: float = 0.15
    head: float = 0.0          # head tilt
    drop: float = 0.0          # extra crouch (pixels at scale 1)


def _lerp_pose(a: Pose, b: Pose, t: float) -> Pose:
    return Pose(**{k: getattr(a, k) + (getattr(b, k) - getattr(a, k)) * t for k in a.__dataclass_fields__})


# ------------------------------------------------------------------ poses

def idle(t: float, seed: float = 0) -> Pose:
    b = math.sin(t * 2.1 + seed) * 0.025
    return Pose(lean=b, sh_f=0.14 + b, sh_b=-0.14 - b, el_f=0.18, el_b=0.12, head=b * 2)


def walk(t: float, speed: float = 1.0) -> Pose:
    ph = t * speed * 2 * math.pi * 0.95
    s = math.sin(ph)
    return Pose(
        lean=0.06,
        hip_f=0.45 * s, knee_f=0.15 + 0.55 * max(0.0, math.sin(ph - 1.3)),
        hip_b=-0.45 * s, knee_b=0.15 + 0.55 * max(0.0, math.sin(ph + math.pi - 1.3)),
        sh_f=-0.38 * s, el_f=0.35, sh_b=0.38 * s, el_b=0.35,
        head=0.03 * math.sin(ph * 2),
    )


def run(t: float, speed: float = 1.0) -> Pose:
    ph = t * speed * 2 * math.pi * 1.45
    s = math.sin(ph)
    return Pose(
        lean=0.32,
        hip_f=0.85 * s + 0.15, knee_f=0.35 + 1.1 * max(0.0, math.sin(ph - 1.1)),
        hip_b=-0.85 * s + 0.15, knee_b=0.35 + 1.1 * max(0.0, math.sin(ph + math.pi - 1.1)),
        sh_f=-0.9 * s, el_f=1.5, sh_b=0.9 * s, el_b=1.5,
        head=-0.1,
    )


def flashlight(t: float, aim: float = 0.0, walking: float = 0.0) -> Pose:
    """Front arm held out (aim: + points up, - down)."""
    p = walk(t, walking) if walking else idle(t)
    p.sh_f = math.pi / 2 - 0.12 + aim
    p.el_f = 0.12
    p.sh_b = 0.35 + (0.1 * math.sin(t * 2) if not walking else p.sh_b * 0.3)
    p.el_b = 1.3
    p.lean = 0.08 if walking else 0.03
    return p


def push(t: float) -> Pose:
    w = math.sin(t * 9) * 0.03
    return Pose(lean=0.38, hip_f=0.55, knee_f=0.45, hip_b=-0.5, knee_b=0.15,
                sh_f=1.45 + w, el_f=0.05, sh_b=1.35 - w, el_b=0.1)


def knock(t: float) -> Pose:
    hit = abs(math.sin(t * 7.5))
    return Pose(lean=0.04, sh_f=2.55 - hit * 0.5, el_f=-0.4 + hit * 0.6, sh_b=-0.1, el_b=0.2)


def scared(t: float) -> Pose:
    sh = math.sin(t * 30) * 0.03
    return Pose(lean=-0.12 + sh, hip_f=0.25, knee_f=0.35, hip_b=-0.2, knee_b=0.35,
                sh_f=2.2, el_f=1.9, sh_b=2.0, el_b=2.0, drop=10)


def crouch(t: float) -> Pose:
    b = math.sin(t * 2) * 0.02
    return Pose(lean=0.45 + b, hip_f=1.15, knee_f=1.9, hip_b=0.75, knee_b=1.7,
                sh_f=0.7, el_f=0.6, sh_b=0.4, el_b=0.8, drop=0)


def listen(t: float) -> Pose:
    """Ear against a door: leaning in, one hand on it."""
    b = math.sin(t * 1.5) * 0.02
    return Pose(lean=0.3 + b, hip_f=0.35, knee_f=0.2, hip_b=-0.35, knee_b=0.1,
                sh_f=1.35, el_f=0.6, sh_b=0.1, el_b=0.3, head=0.35)


def reach(t: float) -> Pose:
    """Creature arms stretched forward."""
    w = noise(t, 3) * 0.08
    return Pose(lean=0.45, hip_f=0.2, knee_f=0.3, hip_b=-0.15, knee_b=0.25,
                sh_f=1.5 + w, el_f=0.1, sh_b=1.35 - w, el_b=0.15, head=0.25)


def lurk(t: float, seed: float = 0) -> Pose:
    """Creature idle: hunched, arms hanging, twitching now and then."""
    tw = noise(t * 1.3, seed)
    jerk = 0.25 if math.sin(t * 2.3 + seed * 5) > 0.97 else 0.0
    return Pose(lean=0.4 + tw * 0.05, hip_f=0.15, knee_f=0.3, hip_b=-0.1, knee_b=0.3,
                sh_f=0.25 + tw * 0.08, el_f=0.1, sh_b=0.05 - tw * 0.05, el_b=0.05,
                head=0.5 + tw * 0.15 + jerk)


def creep(t: float, speed: float = 0.6) -> Pose:
    p = walk(t, speed)
    p.lean = 0.45
    p.sh_f, p.sh_b = 0.9 + p.sh_f * 0.3, 0.75 + p.sh_b * 0.3
    p.el_f = p.el_b = 0.15
    p.head = 0.35
    return p


POSES = {
    "idle": idle, "walk": walk, "run": run, "push": push, "knock": knock,
    "scared": scared, "crouch": crouch, "listen": listen, "flashlight": flashlight,
    "reach": reach, "lurk": lurk, "creep": creep,
}


def pose_for(action: str, t: float, **kw) -> Pose:
    fn = POSES.get(action, idle)
    if action == "flashlight":
        return fn(t, kw.get("aim", 0.0), kw.get("walking", 0.0))
    if action in ("walk", "run", "creep"):
        return fn(t, kw.get("speed", 1.0))
    if action in ("idle", "lurk"):
        return fn(t, kw.get("seed", 0.0))
    return fn(t)


# ------------------------------------------------------------------ drawing

@dataclass
class Joints:
    hip: tuple
    neck: tuple
    head: tuple
    knee_f: tuple
    foot_f: tuple
    knee_b: tuple
    foot_b: tuple
    elbow_f: tuple
    hand_f: tuple
    elbow_b: tuple
    hand_b: tuple
    hand_angle: float  # direction of the front forearm (screen radians, 0 = right)


def _vec(angle: float, length: float, facing: int) -> tuple[float, float]:
    return (math.sin(angle) * length * facing, math.cos(angle) * length)


def solve(p: Pose, x: float, ground: float, scale: float, facing: int, long_limbs: float = 1.0) -> Joints:
    s = scale
    th, sh, up, fo = THIGH * s * long_limbs, SHIN * s * long_limbs, UPPER * s * long_limbs, FORE * s * long_limbs

    def add(a, b):
        return (a[0] + b[0], a[1] + b[1])

    hip0 = (0.0, 0.0)
    kf = add(hip0, _vec(p.hip_f, th, facing))
    ff = add(kf, _vec(p.hip_f - p.knee_f, sh, facing))
    kb = add(hip0, _vec(p.hip_b, th, facing))
    fb = add(kb, _vec(p.hip_b - p.knee_b, sh, facing))
    lowest = max(ff[1], fb[1])
    hip = (x, ground - lowest + p.drop * s)
    dx, dy = hip[0] - hip0[0], hip[1] - hip0[1]

    def mv(pt):
        return (pt[0] + dx, pt[1] + dy)

    neck = add(hip, (math.sin(p.lean) * TORSO * s * facing, -math.cos(p.lean) * TORSO * s))
    head = add(neck, (math.sin(p.lean + p.head) * (HEAD + 6) * s * facing, -math.cos(p.lean + p.head) * (HEAD + 6) * s))
    shoulder = add(neck, (math.sin(p.lean) * 6 * s * facing, math.cos(p.lean) * 6 * s))
    ef = add(shoulder, _vec(p.sh_f, up, facing))
    hf = add(ef, _vec(p.sh_f + p.el_f, fo, facing))
    eb = add(shoulder, _vec(p.sh_b, up, facing))
    hb = add(eb, _vec(p.sh_b + p.el_b, fo, facing))
    a = p.sh_f + p.el_f
    hand_angle = math.atan2(math.cos(a), math.sin(a) * facing)
    return Joints(hip, neck, head, mv(kf), mv(ff), mv(kb), mv(fb), ef, hf, eb, hb, hand_angle)


def draw_stickman(ctx: cairo.Context, pose: Pose, x: float, ground: float, scale: float = 1.25,
                  facing: int = 1, color: str = "#f2f2f2", outline: str = "#1b1b1b",
                  alpha: float = 1.0, prop: str | None = None) -> Joints:
    """The hero. `prop` = 'flashlight' puts a torch in the front hand."""
    j = solve(pose, x, ground, scale, facing)
    w = 13 * scale
    back = "#bdbdbd" if color == "#f2f2f2" else color
    stroke_line(ctx, [j.hip, j.knee_b, j.foot_b], w, back, alpha, outline)
    stroke_line(ctx, [j.neck, j.elbow_b, j.hand_b], w, back, alpha, outline)
    stroke_line(ctx, [j.hip, j.neck], w, color, alpha, outline)
    stroke_line(ctx, [j.hip, j.knee_f, j.foot_f], w, color, alpha, outline)
    if prop == "flashlight":
        draw_flashlight(ctx, j.hand_f, j.hand_angle, scale, alpha)
    stroke_line(ctx, [j.neck, j.elbow_f, j.hand_f], w, color, alpha, outline)
    r = HEAD * scale
    ctx.arc(j.head[0], j.head[1], r + 3, 0, 2 * math.pi)
    set_color(ctx, outline, alpha)
    ctx.fill()
    ctx.arc(j.head[0], j.head[1], r, 0, 2 * math.pi)
    set_color(ctx, color, alpha)
    ctx.fill()
    return j


def draw_flashlight(ctx, hand, angle, scale=1.0, alpha=1.0, on=True):
    ctx.save()
    ctx.translate(*hand)
    ctx.rotate(angle)
    L, R = 46 * scale, 9 * scale
    ctx.rectangle(-8 * scale, -R, L, 2 * R)
    set_color(ctx, "#2c2f36", alpha)
    ctx.fill()
    ctx.rectangle(L - 12 * scale, -R * 1.45, 16 * scale, R * 2.9)
    set_color(ctx, "#4a4f59", alpha)
    ctx.fill()
    if on:
        ctx.rectangle(L + 3 * scale, -R * 1.2, 3 * scale, R * 2.4)
        set_color(ctx, "#fff6d6", alpha)
        ctx.fill()
    ctx.restore()


def flashlight_tip(j: Joints, scale: float) -> tuple[float, float]:
    L = 52 * scale
    return (j.hand_f[0] + math.cos(j.hand_angle) * L, j.hand_f[1] + math.sin(j.hand_angle) * L)


def draw_creature(ctx: cairo.Context, pose: Pose, x: float, ground: float, scale: float = 1.25,
                  facing: int = -1, alpha: float = 1.0, eye_alpha: float = 1.0,
                  body: bool = True) -> Joints:
    """Tall, thin, too-long limbs, glowing eyes. Mostly seen as eyes in the dark."""
    j = solve(pose, x, ground, scale * 1.18, facing, long_limbs=1.35)
    if body and alpha > 0:
        w = 9 * scale
        col, out = "#0c0d10", "#34363d"
        for pts in ([j.hip, j.knee_b, j.foot_b], [j.neck, j.elbow_b, j.hand_b], [j.hip, j.neck],
                    [j.hip, j.knee_f, j.foot_f], [j.neck, j.elbow_f, j.hand_f]):
            stroke_line(ctx, pts, w, col, alpha, out, outline_extra=4)
        # long fingers
        for hand, el in ((j.hand_f, j.elbow_f), (j.hand_b, j.elbow_b)):
            a = math.atan2(hand[1] - el[1], hand[0] - el[0])
            for k in (-0.35, 0, 0.35):
                tip = (hand[0] + math.cos(a + k) * 16 * scale, hand[1] + math.sin(a + k) * 16 * scale)
                stroke_line(ctx, [hand, tip], 3.5 * scale, col, alpha)
        r = HEAD * scale * 1.05
        ctx.save()
        ctx.translate(*j.head)
        ctx.scale(0.85, 1.15)
        ctx.arc(0, 0, r + 2, 0, 2 * math.pi)
        set_color(ctx, out, alpha)
        ctx.fill()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        set_color(ctx, col, alpha)
        ctx.fill()
        ctx.restore()
    eyes(ctx, j.head[0] + 5 * scale * facing, j.head[1] - 2 * scale, 4.2 * scale, eye_alpha)
    return j


def draw_shadow(ctx, x, ground, scale=1.0, alpha=0.35):
    ctx.save()
    ctx.translate(x, ground + 4)
    ctx.scale(1, 0.18)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 70 * scale)
    g.add_color_stop_rgba(0, 0, 0, 0, alpha)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, 70 * scale, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


__all__ = ["Pose", "pose_for", "draw_stickman", "draw_creature", "draw_flashlight", "flashlight_tip",
           "draw_shadow", "replace", "glow", "_lerp_pose"]
