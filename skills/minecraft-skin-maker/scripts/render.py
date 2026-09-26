"""Orthographic ray renderer; texture samples come only from the exported PNG."""
import hashlib
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from uv import PARTS, dimensions, layout


def bounds(part, model, layer):
    w, h, d = dimensions(part, model)
    x = 0 if part in ("head", "body") else (-1 if part.startswith("right") else 1) * (4 + w/2 if "arm" in part else 2)
    y = 28 if part == "head" else 18 if part == "body" or "arm" in part else 6
    grow = (0.5 if part == "head" else 0.25) if layer == "outer" else 0
    return np.array([x-w/2-grow, y-h/2-grow, -d/2-grow]), np.array([x+w/2+grow, y+h/2+grow, d/2+grow])


def surface_uv(points, lo, hi, face):
    q = (points - lo) / (hi - lo)
    x, y, z = q[..., 0], q[..., 1], q[..., 2]
    if face == "front": return x, 1-y
    if face == "back": return 1-x, 1-y
    if face == "right": return z, 1-y
    if face == "left": return 1-z, 1-y
    # The bottom atlas tile shares the top tile's back-to-front v direction.
    return x, z


def camera(yaw=0, pitch=0):
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    right = np.array([math.cos(yaw), 0, -math.sin(yaw)])
    toward = np.array([math.sin(yaw)*math.cos(pitch), math.sin(pitch), math.cos(yaw)*math.cos(pitch)])
    up = np.cross(toward, right)
    return right, up, toward


def render_view(texture, model, yaw=0, pitch=0, width=360, height=480, scale=12, lighting=True, layers=("base", "outer")):
    """Sort ray intersections per pixel, including both sides of outer layers."""
    tex = np.asarray(texture.convert("RGBA"))
    right, up, toward = camera(yaw, pitch)
    xx, yy = np.meshgrid((np.arange(width)+0.5-width/2)/scale, (height/2-np.arange(height)-0.5)/scale)
    origins = xx[..., None]*right + yy[..., None]*up + np.array([0, 16, 0])
    axes = {"front": (2, 1), "back": (2, -1), "right": (0, -1),
            "left": (0, 1), "top": (1, 1), "bottom": (1, -1)}
    shade = {"front": 1, "back": .87, "right": .83, "left": .91, "top": 1.07, "bottom": .69}
    depths, rgba = [], []
    for f in layout(model).values():
        if f.layer not in layers:
            continue
        axis, sign = axes[f.face]
        if abs(toward[axis]) < 1e-8 or (f.layer == "base" and toward[axis]*sign < 0):
            continue
        lo, hi = bounds(f.part, model, f.layer)
        plane = hi[axis] if sign == 1 else lo[axis]
        t = (plane-origins[..., axis])/toward[axis]
        point = origins+t[..., None]*toward
        valid = np.all((point >= lo-1e-7) & (point <= hi+1e-7), axis=-1)
        u, v = surface_uv(point, lo, hi, f.face)
        tx = f.x+np.clip(np.floor(u*f.w).astype(int), 0, f.w-1)
        ty = f.y+np.clip(np.floor(v*f.h).astype(int), 0, f.h-1)
        sample = tex[ty, tx].copy()
        sample[..., 3] = np.where(valid, sample[..., 3], 0)
        if lighting:
            sample[..., :3] = np.minimum(255, sample[..., :3].astype(float)*shade[f.face]).astype(np.uint8)
        depths.append(np.where(valid, t, -np.inf).astype(np.float32))
        rgba.append(sample)
    background = np.empty((height, width, 4), dtype=np.uint8)
    background[:] = [238, 241, 244, 255]
    # A small ground shadow gives the static body an unambiguous floor.
    if pitch >= 0 and abs(pitch) < 80:
        foot = np.array([0, 0, 0])-np.array([0, 16, 0])
        cy = height/2-float(foot @ up)*scale+3
        sy, sx = np.mgrid[:height, :width]
        ellipse = ((sx-width/2)/(6.7*scale))**2+((sy-cy)/(0.45*scale))**2 < 1
        background[ellipse, :3] = [213, 219, 224]
    if not depths:
        return Image.fromarray(background)
    stack = np.stack(rgba)
    order = np.argsort(np.stack(depths), axis=0, kind="stable")
    rr, cc = np.indices((height, width))
    out = background[..., :3].astype(float)
    for rank in order:
        pixels = stack[rank, rr, cc]
        a = pixels[..., 3:4]/255
        out = pixels[..., :3]*a + out*(1-a)
    background[..., :3] = out.astype(np.uint8)
    return Image.fromarray(background)


def angle_preview(png, model, destination, yaw=0, pitch=0):
    """Render an additional inspection angle directly from the exported texture."""
    if not math.isfinite(yaw) or not math.isfinite(pitch) or not -90 <= pitch <= 90:
        raise ValueError("Preview angles must be finite; pitch must be between -90 and 90 degrees")
    png, destination = Path(png), Path(destination)
    output = destination / "custom-view.png"
    if output.resolve() == png.resolve():
        raise ValueError("Choose a separate output directory so the source skin stays unchanged")
    with Image.open(png) as source:
        texture = source.convert("RGBA")
    if texture.size != (64, 64):
        raise ValueError("Preview source must be the exported 64x64 PNG")
    view = render_view(texture, model, yaw, pitch)
    destination.mkdir(parents=True, exist_ok=True)
    view.save(output)
    return {"texture_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
            "model": model, "view": str(output), "yaw": yaw, "pitch": pitch,
            "in_game_tested": False}


def previews(png, model, destination, title="Minecraft skin"):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with Image.open(png) as source:
        texture = source.convert("RGBA")
    if texture.size != (64, 64):
        raise ValueError("Preview source must be the exported 64x64 PNG")
    views = [("front", 0, 0, "FRONT"), ("back", 180, 0, "BACK"),
             ("three-quarter", -33, 16, "THREE-QUARTER")]
    sheet = Image.new("RGB", (1140, 624), "#eef1f4")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=28)
    small = ImageFont.load_default(size=15)
    # Clamp visible title length; keep the complete Unicode name in the design.
    display_title = title if len(title) <= 50 else title[:47]+"..."
    draw.text((30, 22), display_title, font=font, fill="#1c2b38")
    draw.text((30, 62), f"{model.title()} arms  /  64 x 64  /  rendered from the exported skin", font=small, fill="#526675")
    paths = []
    for i, (name, yaw, pitch, label) in enumerate(views):
        view = render_view(texture, model, yaw, pitch)
        path = destination/f"{name}.png"
        view.save(path)
        paths.append(str(path))
        sheet.paste(view.convert("RGB"), (10+i*380, 103))
        draw.text((190+i*380, 598), label, font=small, anchor="mm", fill="#526675")
    sheet.save(destination/"preview.png")
    return {"texture_sha256": hashlib.sha256(Path(png).read_bytes()).hexdigest(),
            "model": model, "views": paths, "contact_sheet": str(destination/"preview.png"),
            "renderer": "orthographic texture ray renderer; base and outer layers", "in_game_tested": False}
