"""Editable, named pixel-art components with strict face-local coordinates."""
import base64
import copy
import io
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw
from uv import PARTS, layout, masks, convert_model


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def color(value, palette):
    value = palette.get(value, value) if isinstance(value, str) else value
    if value in ("transparent", None):
        return (0, 0, 0, 0)
    if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", value):
        b = bytes.fromhex(value[1:])
        return tuple(b) if len(b) == 4 else (*b, 255)
    raise ValueError(f"Unknown palette color or invalid #RRGGBB[AA]: {value!r}")


def fresh(name="My Skin", model="classic"):
    layout(model)
    return {"schema_version": 1, "name": name, "model": model, "canvas_model": model,
            "palette": {"foundation": "#a57760"},
            "base": {part: "foundation" for part in PARTS}, "components": [],
            "notes": []}


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


# Unknown keys are errors: a misspelled key such as "colour" or "paints" would
# otherwise be ignored and silently drop part of the design.
DESIGN_KEYS = {"schema_version", "name", "model", "canvas_model", "palette", "base", "symbols",
               "components", "notes", "reference_brief", "request", "description", "source_png"}
COMPONENT_KEYS = {"id", "paint", "note", "notes", "description"}
OPERATION_KEYS = {
    "fill": ({"color"}, set()),
    "rect": ({"box", "color"}, set()),
    "points": ({"points", "color"}, set()),
    "line": ({"points", "color"}, {"width"}),
    "polygon": ({"points", "color"}, set()),
    "pixels": ({"rows"}, {"at", "map"}),
}


def _keys(where, found, required, optional):
    missing = sorted(required - set(found))
    unknown = sorted(set(found) - required - optional)
    problems = []
    if missing:
        problems.append(f"missing {', '.join(missing)}")
    if unknown:
        problems.append(f"unknown key {', '.join(unknown)} (allowed: {', '.join(sorted(required | optional))})")
    if problems:
        raise ValueError(f"{where}: {'; '.join(problems)}")


def check_structure(data):
    """Reject malformed designs with a message that names the exact location."""
    if not isinstance(data, dict):
        raise ValueError("Design must be a JSON object")
    _keys("design", data, {"schema_version"}, DESIGN_KEYS)
    if data["schema_version"] != 1:
        raise ValueError("design schema_version must be 1")
    for key in ("model", "canvas_model"):
        if data.get(key, "classic") not in ("classic", "slim"):
            raise ValueError(f"design {key} must be classic or slim")
    for key in ("palette", "base", "symbols"):
        if not isinstance(data.get(key, {}), dict):
            raise ValueError(f"design {key} must be an object")
    for symbol in data.get("symbols", {}):
        if len(symbol) != 1 or symbol == ".":
            raise ValueError(f"symbols key {symbol!r} must be one character other than '.'")
    components = data.get("components", [])
    if not isinstance(components, list):
        raise ValueError("design components must be a list")
    identifiers = set()
    for index, component in enumerate(components):
        where = f"components[{index}]"
        if not isinstance(component, dict):
            raise ValueError(f"{where} must be an object")
        _keys(where, component, {"id", "paint"}, COMPONENT_KEYS - {"id", "paint"})
        identifier = component["id"]
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(f"{where}: id must be a non-empty string")
        if identifier in identifiers:
            raise ValueError(f"Component IDs must be unique: {identifier}")
        identifiers.add(identifier)
        if not isinstance(component["paint"], list):
            raise ValueError(f"{identifier}: paint must be a list")
        for number, operation in enumerate(component["paint"]):
            spot = f"{identifier}, paint[{number}]"
            if not isinstance(operation, dict):
                raise ValueError(f"{spot} must be an object")
            kind = operation.get("op")
            if kind not in OPERATION_KEYS:
                raise ValueError(f"{spot}: op must be one of {', '.join(OPERATION_KEYS)}; got {kind!r}")
            required, optional = OPERATION_KEYS[kind]
            _keys(f"{spot} ({kind})", operation, required | {"op", "target"}, optional)
            targets = operation["target"]
            if isinstance(targets, str):
                targets = [targets]
            if not isinstance(targets, list) or not targets or not all(isinstance(t, str) for t in targets):
                raise ValueError(f"{spot}: target must be a face name or a non-empty list of face names")


def _point(point, w, h):
    if not isinstance(point, (list, tuple)) or len(point) != 2 or not all(_integer(n) for n in point):
        raise ValueError(f"Pixel point must have two integers: {point!r}")
    if not (0 <= point[0] < w and 0 <= point[1] < h):
        raise ValueError(f"Pixel point {point} is outside {w}x{h} face")
    return tuple(point)


def _paint(tile, operation, palette, symbols=None):
    w, h = tile.size
    kind = operation["op"]
    brush = ImageDraw.Draw(tile)
    ink = color(operation["color"], palette) if "color" in operation else None
    if kind == "fill":
        tile.paste(ink, (0, 0, w, h))
    elif kind == "rect":
        box = operation["box"]
        if len(box) != 4 or not all(_integer(n) for n in box):
            raise ValueError("rect box must be [x,y,width,height] integers")
        x, y, rw, rh = box
        if rw <= 0 or rh <= 0:
            raise ValueError("rect dimensions must be positive")
        _point((x, y), w, h)
        _point((x+rw-1, y+rh-1), w, h)
        brush.rectangle((x, y, x+rw-1, y+rh-1), fill=ink)
    elif kind in ("line", "polygon", "points"):
        points = [_point(p, w, h) for p in operation["points"]]
        if not points:
            raise ValueError("points may not be empty")
        if kind == "line":
            width = operation.get("width", 1)
            if not _integer(width) or width < 1:
                raise ValueError("line width must be a positive integer")
            brush.line(points, fill=ink, width=width)
        elif kind == "polygon":
            if len(points) < 3:
                raise ValueError("polygon needs at least three vertices")
            brush.polygon(points, fill=ink)
        else:
            brush.point(points, fill=ink)
    elif kind == "pixels":
        at = operation.get("at", [0, 0])
        if not isinstance(at, (list, tuple)) or len(at) != 2 or not all(_integer(n) for n in at):
            raise ValueError(f"pixels at must be two integers: {at!r}")
        x, y = at
        # An operation's own map overrides the design-wide symbols.
        symbols = {**(symbols or {}), **operation.get("map", {})}
        rows = operation["rows"]
        if not isinstance(rows, list) or not rows or not all(isinstance(row, str) and row for row in rows):
            raise ValueError("pixels rows must be a list of non-empty strings")
        for dy, row in enumerate(rows):
            for dx, symbol in enumerate(row):
                _point((x+dx, y+dy), w, h)
                if symbol != ".":
                    if symbol not in symbols:
                        raise ValueError(f"No palette mapping for pixel symbol {symbol}")
                    tile.putpixel((x+dx, y+dy), color(symbols[symbol], palette))
    else:
        raise ValueError(f"Unknown paint operation: {kind}")


def assemble(data):
    check_structure(data)
    model = data.get("model", "classic")
    canvas = data.get("canvas_model", model)
    faces = layout(canvas)
    palette = data.get("palette", {})
    if "source_png" in data:
        image = Image.open(io.BytesIO(base64.b64decode(data["source_png"], validate=True))).convert("RGBA")
        if image.size != (64, 64):
            raise ValueError("embedded source must be 64x64")
    else:
        image = Image.new("RGBA", (64, 64))
        for f in faces.values():
            if f.layer == "base":
                if f.part not in data.get("base", {}):
                    raise ValueError(f"Missing base color for {f.part}")
                ink = color(data["base"][f.part], palette)
                if ink[3] != 255:
                    raise ValueError(f"Base color must be opaque for {f.part}")
                image.paste(ink, f.box)
    symbols = data.get("symbols", {})
    for component in data.get("components", []):
        identifier = component["id"]
        for operation in component["paint"]:
            targets = operation["target"]
            targets = [targets] if isinstance(targets, str) else targets
            for target in targets:
                if target not in faces:
                    raise ValueError(f"{identifier}: unknown face {target!r}; use part.layer.face such as head.outer.front")
                f = faces[target]
                tile = image.crop(f.box)
                try:
                    _paint(tile, operation, palette, symbols)
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"{identifier}, {target}: {exc}") from exc
                # Report layer rule violations where they were painted, not as an atlas-wide count.
                alpha = tile.getchannel("A").getdata()
                if f.layer == "base" and any(a != 255 for a in alpha):
                    raise ValueError(f"{identifier}, {target}: base pixels must stay opaque; paint transparency on the outer layer")
                if f.layer == "outer" and any(a not in (0, 255) for a in alpha):
                    raise ValueError(f"{identifier}, {target}: outer pixels need alpha 0 or 255, not partial transparency")
                image.paste(tile, f.box)
    return convert_model(image, canvas, model)


def validate_image(image, model):
    errors = []
    if image.size != (64, 64):
        return {"ok": False, "errors": [f"Expected 64x64, got {image.size}"], "model": model}
    if image.mode != "RGBA":
        errors.append(f"Expected RGBA, got {image.mode}")
    image = image.convert("RGBA")
    alpha = list(image.getchannel("A").getdata())
    mm = masks(model)
    base = list(mm["base"].getdata())
    outer = list(mm["outer"].getdata())
    used = list(mm["used"].getdata())
    nonopaque = sum(bool(b and a != 255) for a, b in zip(alpha, base))
    unused = sum(bool(not u and a != 0) for a, u in zip(alpha, used))
    fractional = sum(bool(o and a not in (0, 255)) for a, o in zip(alpha, outer))
    if nonopaque:
        errors.append(f"{nonopaque} used base pixels are not fully opaque")
    if unused:
        errors.append(f"{unused} unused pixels are not transparent")
    if fractional:
        errors.append(f"{fractional} outer pixels have partial alpha; use 0 or 255 for consistent Java/Bedrock output")
    return {"ok": not errors, "model": model, "size": [64, 64],
            "base_pixels": sum(bool(b) for b in base),
            "outer_visible_pixels": sum(bool(a and b) for a, b in zip(alpha, outer)),
            "errors": errors}


def validate_png(path, model):
    with Image.open(path) as image:
        if image.format != "PNG":
            return {"ok": False, "errors": ["File is not a PNG"]}
        image.load()
        return validate_image(image, model)


def import_skin(path, name=None, model="auto"):
    with Image.open(path) as source:
        if source.format != "PNG" or source.size not in ((64, 64), (64, 32)):
            raise ValueError("Existing skin import accepts 64x64 or legacy 64x32 PNGs")
        source.load()
        image = source.convert("RGBA")
    notes = []
    if image.size == (64, 32):
        canvas = Image.new("RGBA", (64, 64))
        canvas.paste(image, (0, 0))
        classic = layout("classic")
        for part in ("arm", "leg"):
            for face in ("front", "back", "left", "right", "top", "bottom"):
                src_face = {"left": "right", "right": "left"}.get(face, face)
                src = classic[f"right_{part}.base.{src_face}"]
                dst = classic[f"left_{part}.base.{face}"]
                canvas.paste(image.crop(src.box).transpose(Image.Transpose.FLIP_LEFT_RIGHT), dst.box)
        image = canvas
        inferred = "classic"
        notes.append("Expanded legacy 64x32 skin; mirrored right limbs to create the left limbs.")
        # Legacy editors often filled an unused hat layer with a solid color; Minecraft
        # treats a hat area with no transparent pixel as empty, so do the same.
        hat = image.crop((32, 0, 64, 16))
        if min(hat.getchannel("A").getdata()) >= 128:
            image.paste((0, 0, 0, 0), (32, 0, 64, 16))
            notes.append("Cleared the fully opaque legacy hat layer, which Minecraft treats as no hat.")
    else:
        classic_base = masks("classic")["base"]
        slim_base = masks("slim")["base"]
        pixels = list(image.getdata())
        cb, sb = list(classic_base.getdata()), list(slim_base.getdata())
        slim_valid = all(p[3] == 255 for p, b in zip(pixels, sb) if b)
        exclusive_empty = all(p[3] == 0 for p, c, s in zip(pixels, cb, sb) if c and not s)
        inferred = "slim" if slim_valid and exclusive_empty else "classic"
        notes.append(f"Model inferred as {inferred}; PNG files do not contain authoritative model metadata.")
    chosen = inferred if model == "auto" else model
    # An explicit model describes the input UV layout, rather than asking for
    # conversion. Use revise --model for a later, separate width conversion.
    if model != "auto" and source.size == (64, 64):
        inferred = chosen
        notes = [f"Used the supplied {chosen} model metadata."]
    image = convert_model(image, inferred, chosen)
    mm = masks(chosen)
    result = Image.new("RGBA", (64, 64))
    repaired = 0
    for y in range(64):
        for x in range(64):
            r, g, b, a = image.getpixel((x, y))
            if mm["base"].getpixel((x, y)):
                repaired += a != 255
                result.putpixel((x, y), (r, g, b, 255))
            elif mm["outer"].getpixel((x, y)):
                repaired += a not in (0, 255)
                result.putpixel((x, y), (r, g, b, 255) if a >= 128 else (0, 0, 0, 0))
    if repaired:
        notes.append(f"Normalized alpha on {repaired} used pixels for compatibility.")
    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    data = fresh(name or Path(path).stem, chosen)
    data["source_png"] = base64.b64encode(buffer.getvalue()).decode("ascii")
    data["notes"] = notes
    return data


def revise(data, palette=None, model=None, name=None):
    result = copy.deepcopy(data)
    if palette:
        for key, value in palette.items():
            if key not in result["palette"]:
                raise ValueError(f"Unknown palette key: {key}")
            color(value, {})
            result["palette"][key] = value
    if model:
        layout(model)
        result["canvas_model"] = result.get("canvas_model", result.get("model", "classic"))
        result["model"] = model
    if name:
        result["name"] = name
    return result
