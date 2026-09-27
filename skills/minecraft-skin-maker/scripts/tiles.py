"""Enlarged, gridded face tiles and per-face pixel differences for exact edits."""
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from uv import PARTS, layout

# Unfolded around the body, so neighbouring tiles share an edge: right|front|left|back.
SHEET_FACES = ("right", "front", "left", "back", "top", "bottom")
CELL = 22


def _load(png):
    with Image.open(png) as source:
        texture = source.convert("RGBA")
    if texture.size != (64, 64):
        raise ValueError(f"{png}: expected a 64x64 skin PNG")
    return texture


def _checker(w, h):
    tile = Image.new("RGB", (w*CELL, h*CELL), "#ffffff")
    draw = ImageDraw.Draw(tile)
    half = CELL//2
    for y in range(0, h*CELL, half):
        for x in range(0, w*CELL, half):
            if (x//half + y//half) % 2:
                draw.rectangle((x, y, x+half-1, y+half-1), fill="#d9dde2")
    return tile


def _face_image(texture, face, highlight=None):
    """One face at CELL pixels per texel, transparent texels shown on a checkerboard."""
    crop = texture.crop(face.box).resize((face.w*CELL, face.h*CELL), Image.Resampling.NEAREST)
    tile = _checker(face.w, face.h)
    tile.paste(crop, (0, 0), crop)
    draw = ImageDraw.Draw(tile)
    for x in range(face.w+1):
        draw.line((x*CELL, 0, x*CELL, face.h*CELL), fill="#7d8791")
    for y in range(face.h+1):
        draw.line((0, y*CELL, face.w*CELL, y*CELL), fill="#7d8791")
    for x, y in highlight or ():
        draw.rectangle((x*CELL, y*CELL, (x+1)*CELL, (y+1)*CELL), outline="#ff2bd6", width=3)
    return tile


def part_sheet(texture, model, part, highlights=None):
    faces = layout(model)
    font = ImageFont.load_default(size=13)
    title = ImageFont.load_default(size=20)
    cols = [faces[f"{part}.base.{name}"] for name in SHEET_FACES]
    col_w = [max(f.w*CELL+44, int(font.getlength(f"{part}.outer.{f.face}  {f.w}x{f.h}"))+16) for f in cols]
    row_h = max(f.h for f in cols)*CELL+52
    sheet = Image.new("RGB", (sum(col_w)+30, 70+2*row_h), "#eef1f4")
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 14), f"{part}  /  {model}  /  face-local x,y: (0,0) is each tile's upper-left",
              font=title, fill="#1c2b38")
    for row, layer in enumerate(("base", "outer")):
        x0 = 20
        y0 = 60+row*row_h
        for name, width in zip(SHEET_FACES, col_w):
            face = faces[f"{part}.{layer}.{name}"]
            ox, oy = x0+30, y0+34
            draw.text((x0, y0), f"{part}.{layer}.{name}  {face.w}x{face.h}", font=font, fill="#1c2b38")
            for x in range(face.w):
                draw.text((ox+x*CELL+CELL//2, oy-4), str(x), font=font, anchor="mb", fill="#526675")
            for y in range(face.h):
                draw.text((ox-5, oy+y*CELL+CELL//2), str(y), font=font, anchor="rm", fill="#526675")
            spots = (highlights or {}).get(face.key)
            sheet.paste(_face_image(texture, face, spots), (ox, oy))
            x0 += width
    return sheet


def face_sheets(png, model, destination, parts=PARTS):
    """Write faces-<part>.png sheets for the requested parts of the exported texture."""
    texture = _load(png)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for part in parts:
        if part not in PARTS:
            raise ValueError(f"Unknown part {part!r}; use one of {', '.join(PARTS)}")
        path = destination/f"faces-{part}.png"
        if path.resolve() == Path(png).resolve():
            raise ValueError("Choose a separate output directory so the source skin stays unchanged")
        part_sheet(texture, model, part).save(path)
        written.append(str(path))
    return {"ok": True, "model": model, "sheets": written,
            "texture_sha256": hashlib.sha256(Path(png).read_bytes()).hexdigest()}


def difference(before_png, after_png, model, destination=None):
    """List changed texels per face; optionally draw them outlined on face sheets."""
    before, after = _load(before_png), _load(after_png)
    a, b = np.asarray(before), np.asarray(after)
    # Fully transparent texels are equal whatever their hidden RGB values.
    changed = np.any(a != b, axis=2) & ~((a[..., 3] == 0) & (b[..., 3] == 0))
    faces = {}
    highlights = {}
    for face in layout(model).values():
        region = changed[face.y:face.y+face.h, face.x:face.x+face.w]
        if region.any():
            ys, xs = np.nonzero(region)
            spots = [(int(x), int(y)) for x, y in zip(xs, ys)]
            highlights[face.key] = spots
            faces[face.key] = {"pixels": len(spots),
                               "box": [int(xs.min()), int(ys.min()), int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)]}
    report = {"ok": True, "model": model, "changed_pixels": int(changed.sum()), "faces": faces}
    if destination and faces:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        parts = [p for p in PARTS if any(k.startswith(p+".") for k in faces)]
        report["sheets"] = []
        for part in parts:
            path = destination/f"diff-{part}.png"
            part_sheet(after, model, part, highlights).save(path)
            report["sheets"].append(str(path))
    return report
