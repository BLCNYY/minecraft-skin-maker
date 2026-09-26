"""Minecraft 64x64 UV nets. Left/right always mean the wearer's side."""
from dataclasses import dataclass
from pathlib import Path
import json
from PIL import Image, ImageDraw

PARTS = ("head", "body", "right_arm", "left_arm", "right_leg", "left_leg")
FACES = ("top", "bottom", "right", "front", "left", "back")
ORIGINS = {
    "head": ((0, 0), (32, 0)), "body": ((16, 16), (16, 32)),
    "right_arm": ((40, 16), (40, 32)), "left_arm": ((32, 48), (48, 48)),
    "right_leg": ((0, 16), (0, 32)), "left_leg": ((16, 48), (0, 48)),
}

@dataclass(frozen=True)
class Face:
    part: str
    layer: str
    face: str
    x: int
    y: int
    w: int
    h: int

    @property
    def key(self):
        return f"{self.part}.{self.layer}.{self.face}"

    @property
    def box(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def dimensions(part, model):
    if model not in ("classic", "slim"):
        raise ValueError("model must be classic or slim")
    if part == "head":
        return (8, 8, 8)
    return (8 if part == "body" else 3 if "arm" in part and model == "slim" else 4, 12, 4)


def layout(model="classic"):
    result = {}
    for part in PARTS:
        w, h, d = dimensions(part, model)
        for layer, (u, v) in zip(("base", "outer"), ORIGINS[part]):
            boxes = ((u+d, v, w, d), (u+d+w, v, w, d),
                     (u, v+d, d, h), (u+d, v+d, w, h),
                     (u+d+w, v+d, d, h), (u+2*d+w, v+d, w, h))
            for face, rect in zip(FACES, boxes):
                item = Face(part, layer, face, *rect)
                result[item.key] = item
    return result


def masks(model):
    result = {name: Image.new("L", (64, 64)) for name in ("base", "outer", "used")}
    for f in layout(model).values():
        result[f.layer].paste(255, f.box)
        result["used"].paste(255, f.box)
    return result


def convert_model(image, old, new):
    """Repack each face independently; never resize the complete texture atlas."""
    if old == new:
        return image.copy()
    out = Image.new("RGBA", (64, 64))
    before = layout(old)
    for key, after in layout(new).items():
        tile = image.crop(before[key].box)
        if tile.size != (after.w, after.h):
            tile = tile.resize((after.w, after.h), Image.Resampling.NEAREST)
        out.paste(tile, after.box)
    return out


def templates(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    colors = {"top": "#d6b95a", "bottom": "#947446", "right": "#5c91b4",
              "front": "#60ac96", "left": "#aa7aba", "back": "#d27d6d"}
    for model in ("classic", "slim"):
        for name, mask in masks(model).items():
            mask.save(destination / f"{model}-{name}-mask.png")
        atlas = Image.new("RGBA", (64, 64))
        data = {}
        for f in layout(model).values():
            tile = Image.new("RGBA", (f.w, f.h), colors[f.face])
            # Two unequal corner marks make every face's orientation visible.
            tile.putpixel((0, 0), (255, 255, 255, 255))
            tile.putpixel((f.w - 1, 0), (25, 25, 25, 255))
            atlas.paste(tile, f.box)
            data[f.key] = [f.x, f.y, f.w, f.h]
        atlas.save(destination / f"{model}-uv-template.png")
        (destination / f"{model}-uv.json").write_text(json.dumps(data, indent=2) + "\n")
