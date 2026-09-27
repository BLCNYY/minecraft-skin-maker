#!/usr/bin/env python3
"""Deterministic Minecraft skin assembly, previews, edits and Bedrock packs."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image
import design
import bedrock
import render
import review
import tiles
import uv


def import_instructions(model, export="both"):
    sections = []
    if export in ("both", "java"):
        sections.append(f"Java: Minecraft Launcher > Java Edition > Skins > New Skin. Browse to skin.png, select {model.title()}, then Save & Use.")
    if export in ("both", "bedrock"):
        sections.append(f"Bedrock on Windows, Android or iOS: open skin.mcpack with Minecraft, then select the imported pack in Dressing Room > Classic Skins. If your device does not open the pack, use Classic Skins > Owned/Import > Choose New Skin and select skin.png, using the {'wide' if model == 'classic' else 'narrow'} arm thumbnail. Menu labels can vary by game version.")
        sections.append("Xbox, PlayStation and Switch do not officially support importing custom skin files. Imported Bedrock skins do not automatically sync across devices. macOS uses Java Edition; there is no native Bedrock client for macOS.")
    sections.append("These files have automated format checks and previews from the exported PNG. Actual in-game import has not been tested by this script.")
    return "\n\n".join(sections) + "\n"


def build(data, destination, export="both", reference=None):
    destination = Path(destination)
    if reference:
        protected = Path(reference).resolve()
        generated = ("skin.png", "design.json", "front.png", "back.png", "three-quarter.png",
                     "three-quarter-left.png", "preview.png", "reference-review.png", "skin.mcpack", "IMPORT.txt", "validation.json")
        if protected in { (destination/name).resolve() for name in generated }:
            raise ValueError("Choose a separate output directory so the reference image stays unchanged")
        # Detect unusable input before writing any output artifacts.
        with Image.open(reference) as reference_source:
            reference_source.verify()
    image = design.assemble(data)
    model = data.get("model", "classic")
    check = design.validate_image(image, model)
    if not check["ok"]:
        raise ValueError("Skin validation failed: " + "; ".join(check["errors"]))
    destination.mkdir(parents=True, exist_ok=True)
    if export == "java" and (destination/"skin.mcpack").exists():
        raise ValueError("Choose a fresh output directory for PNG-only delivery; this directory contains an earlier Bedrock pack")
    png = destination/"skin.png"
    image.save(png, format="PNG")
    design.write(destination/"design.json", data)
    preview = render.previews(png, model, destination, data.get("name", "Minecraft skin"))
    report = {"texture": check, "texture_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
              "previews": preview, "visual_inspection": "pending", "in_game_test": "not performed"}
    if reference:
        report["reference_review"] = review.reference_review(png,reference,model,destination,data.get("name","Reference review"))
    if export in ("both", "bedrock"):
        pack = destination/"skin.mcpack"
        report["bedrock"] = bedrock.package(png, pack, data.get("name", "My Skin"), model)
        if not report["bedrock"]["ok"]:
            raise ValueError("Pack validation failed: " + "; ".join(report["bedrock"]["errors"]))
    (destination/"IMPORT.txt").write_text(import_instructions(model, export), encoding="utf-8")
    design.write(destination/"validation.json", report)
    return {"ok": True, "directory": str(destination.resolve()), "model": model,
            "skin": str(png.resolve()), "preview": str((destination/"preview.png").resolve()),
            "reference_review": str((destination/"reference-review.png").resolve()) if reference else None,
            "bedrock_pack": str((destination/"skin.mcpack").resolve()) if export != "java" else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create editable blank design JSON")
    init.add_argument("output")
    init.add_argument("--name", default="My Skin")
    init.add_argument("--model", choices=("classic", "slim"), default="classic")
    make = sub.add_parser("build", help="Assemble, validate, preview and package a design")
    make.add_argument("design")
    make.add_argument("--out", required=True)
    make.add_argument("--export", choices=("both", "java", "bedrock"), default="both")
    make.add_argument("--reference", help="Create a comparison with the supplied reference image")
    validate = sub.add_parser("validate", help="Check a PNG or mcpack")
    validate.add_argument("input")
    validate.add_argument("--model", choices=("classic", "slim"), default="classic")
    validate.add_argument("--png", help="For pack checks, require exact bytes from this PNG")
    preview = sub.add_parser("preview", help="Render the exported PNG, including outer layers")
    preview.add_argument("png")
    preview.add_argument("--model", choices=("classic", "slim"), default="classic")
    preview.add_argument("--out", required=True)
    preview.add_argument("--name", default="Minecraft skin")
    preview.add_argument("--yaw", type=float, help="Render a single view at this horizontal angle in degrees")
    preview.add_argument("--pitch", type=float, help="Render a single view at this vertical angle, from -90 to 90 degrees")
    compare = sub.add_parser("review", help="Compare a reference with fresh renders of the actual PNG")
    compare.add_argument("png")
    compare.add_argument("--reference", required=True)
    compare.add_argument("--model", choices=("classic","slim"), default="classic")
    compare.add_argument("--out", required=True)
    compare.add_argument("--name", default="Reference review")
    pack = sub.add_parser("pack", help="Package a validated PNG as a free skin pack")
    pack.add_argument("png")
    pack.add_argument("--out", required=True)
    pack.add_argument("--name", default="My Skin")
    pack.add_argument("--model", choices=("classic", "slim"), default="classic")
    edit = sub.add_parser("revise", help="Change palette colors or arm width without redrawing")
    edit.add_argument("design")
    edit.add_argument("--out", required=True, help="New design JSON path")
    edit.add_argument("--set", action="append", default=[], metavar="KEY=#RRGGBB")
    edit.add_argument("--model", choices=("classic", "slim"))
    edit.add_argument("--name")
    imp = sub.add_parser("import", help="Import a 64x64 or legacy 64x32 skin into editable JSON")
    imp.add_argument("png")
    imp.add_argument("--out", required=True)
    imp.add_argument("--name")
    imp.add_argument("--model", choices=("auto", "classic", "slim"), default="auto")
    grid = sub.add_parser("faces", help="Enlarged, gridded face tiles with face-local coordinates")
    grid.add_argument("png")
    grid.add_argument("--model", choices=("classic", "slim"), default="classic")
    grid.add_argument("--part", action="append", choices=uv.PARTS, help="Repeat for several parts; default all")
    grid.add_argument("--out", required=True)
    diff = sub.add_parser("diff", help="List changed pixels per face between two skin PNGs")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--model", choices=("classic", "slim"), default="classic")
    diff.add_argument("--out", help="Also write face sheets with changed pixels outlined")
    template = sub.add_parser("templates", help="Generate both models' UV guides and masks")
    template.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            design.write(args.output, design.fresh(args.name, args.model))
            result = {"ok": True, "design": args.output}
        elif args.command == "build":
            result = build(design.read(args.design), args.out, args.export, args.reference)
        elif args.command == "validate":
            result = bedrock.validate_pack(args.input, args.model, args.png) if Path(args.input).suffix.lower() == ".mcpack" else design.validate_png(args.input, args.model)
        elif args.command == "preview":
            result = design.validate_png(args.png, args.model)
            if result["ok"]:
                if args.yaw is not None or args.pitch is not None:
                    result.update(render.angle_preview(args.png, args.model, args.out,
                                                       args.yaw if args.yaw is not None else 0,
                                                       args.pitch if args.pitch is not None else 0))
                else:
                    result.update(render.previews(args.png, args.model, args.out, args.name))
        elif args.command == "pack":
            result = bedrock.package(args.png, args.out, args.name, args.model)
        elif args.command == "review":
            result = {"ok":True,**review.reference_review(args.png,args.reference,args.model,args.out,args.name)}
        elif args.command == "revise":
            if any("=" not in item for item in args.set):
                raise ValueError("--set expects KEY=#RRGGBB, for example --set 'jacket=#a43d47'")
            palette = dict(item.split("=", 1) for item in args.set)
            revised = design.revise(design.read(args.design), palette, args.model, args.name)
            design.write(args.out, revised)
            result = {"ok": True, "design": args.out}
        elif args.command == "import":
            data = design.import_skin(args.png, args.name, args.model)
            design.write(args.out, data)
            result = {"ok": True, "design": args.out, "model": data["model"], "notes": data["notes"]}
        elif args.command == "faces":
            result = tiles.face_sheets(args.png, args.model, args.out, args.part or uv.PARTS)
        elif args.command == "diff":
            result = tiles.difference(args.before, args.after, args.model, args.out)
        elif args.command == "templates":
            uv.templates(args.out)
            result = {"ok": True, "templates": args.out}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok", True) else 1
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
