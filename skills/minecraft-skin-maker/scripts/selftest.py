#!/usr/bin/env python3
"""Independent UV fixtures, rendering orientation, edit and packaging checks."""
import argparse
import copy
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
import bedrock
import design
import render
import review
import tiles
import uv

# Hand-specified atlas rectangles: top,bottom,right,front,left,back.
# These are deliberately independent of uv.layout and its net calculation.
CLASSIC = {
 "head.base": [(8,0,8,8),(16,0,8,8),(0,8,8,8),(8,8,8,8),(16,8,8,8),(24,8,8,8)],
 "head.outer": [(40,0,8,8),(48,0,8,8),(32,8,8,8),(40,8,8,8),(48,8,8,8),(56,8,8,8)],
 "body.base": [(20,16,8,4),(28,16,8,4),(16,20,4,12),(20,20,8,12),(28,20,4,12),(32,20,8,12)],
 "body.outer": [(20,32,8,4),(28,32,8,4),(16,36,4,12),(20,36,8,12),(28,36,4,12),(32,36,8,12)],
 "right_arm.base": [(44,16,4,4),(48,16,4,4),(40,20,4,12),(44,20,4,12),(48,20,4,12),(52,20,4,12)],
 "right_arm.outer": [(44,32,4,4),(48,32,4,4),(40,36,4,12),(44,36,4,12),(48,36,4,12),(52,36,4,12)],
 "left_arm.base": [(36,48,4,4),(40,48,4,4),(32,52,4,12),(36,52,4,12),(40,52,4,12),(44,52,4,12)],
 "left_arm.outer": [(52,48,4,4),(56,48,4,4),(48,52,4,12),(52,52,4,12),(56,52,4,12),(60,52,4,12)],
 "right_leg.base": [(4,16,4,4),(8,16,4,4),(0,20,4,12),(4,20,4,12),(8,20,4,12),(12,20,4,12)],
 "right_leg.outer": [(4,32,4,4),(8,32,4,4),(0,36,4,12),(4,36,4,12),(8,36,4,12),(12,36,4,12)],
 "left_leg.base": [(20,48,4,4),(24,48,4,4),(16,52,4,12),(20,52,4,12),(24,52,4,12),(28,52,4,12)],
 "left_leg.outer": [(4,48,4,4),(8,48,4,4),(0,52,4,12),(4,52,4,12),(8,52,4,12),(12,52,4,12)],
}
SLIM_ARMS = {
 "right_arm.base": [(44,16,3,4),(47,16,3,4),(40,20,4,12),(44,20,3,12),(47,20,4,12),(51,20,3,12)],
 "right_arm.outer": [(44,32,3,4),(47,32,3,4),(40,36,4,12),(44,36,3,12),(47,36,4,12),(51,36,3,12)],
 "left_arm.base": [(36,48,3,4),(39,48,3,4),(32,52,4,12),(36,52,3,12),(39,52,4,12),(43,52,3,12)],
 "left_arm.outer": [(52,48,3,4),(55,48,3,4),(48,52,4,12),(52,52,3,12),(55,52,4,12),(59,52,3,12)],
}
FACE_ORDER = ("top", "bottom", "right", "front", "left", "back")
CORNERS = [(255,41,63,255),(25,224,106,255),(48,107,255,255),(255,219,36,255)]


def fixture(model, only_head=False, outer=False):
    atlas = Image.new("RGBA", (64,64))
    table = {**CLASSIC, **(SLIM_ARMS if model == "slim" else {})}
    for index, (part, rects) in enumerate(table.items()):
        if only_head and part != "head.base":
            continue
        if part.endswith("outer") and not outer:
            continue
        for face, (x,y,w,h) in zip(FACE_ORDER, rects):
            tile = Image.new("RGBA", (w,h), (50+index*13%180,85,125,255))
            for point, ink in zip([(0,0),(w-1,0),(0,h-1),(w-1,h-1)], CORNERS):
                tile.putpixel(point,ink)
            atlas.paste(tile,(x,y))
    return atlas


class SkinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_independent_atlas_rectangles(self):
        for model in ("classic","slim"):
            table = {**CLASSIC, **(SLIM_ARMS if model == "slim" else {})}
            expected = {f"{p}.{f}": tuple(r) for p, rs in table.items() for f,r in zip(FACE_ORDER,rs)}
            actual = {k:(f.x,f.y,f.w,f.h) for k,f in uv.layout(model).items()}
            self.assertEqual(expected,actual)

    def test_masks_are_disjoint_and_complete(self):
        for model,count in (("classic",1632),("slim",1568)):
            mm=uv.masks(model)
            a,b=np.array(mm["base"])>0,np.array(mm["outer"])>0
            self.assertEqual(int(a.sum()),count)
            self.assertEqual(int(b.sum()),count)
            self.assertFalse(np.any(a&b))
            self.assertTrue(np.array_equal(a|b,np.array(mm["used"])>0))

    def test_six_face_corner_orientation(self):
        # Expected screen corners are specified independently for six cardinal views.
        # Bottom v=0 is at the bottom of its underside view, unlike the top view.
        texture=fixture("classic",only_head=True)
        for yaw,pitch,bottom in ((0,0,False),(180,0,False),(-90,0,False),(90,0,False),(0,90,False),(0,-90,True)):
            view=render.render_view(texture,"classic",yaw,pitch,100,160,4,lighting=False,layers=("base",))
            y0,y1=(66,94) if pitch else (18,46)
            expected=CORNERS if not bottom else [CORNERS[2],CORNERS[3],CORNERS[0],CORNERS[1]]
            for point,ink in zip([(36,y0),(64,y0),(36,y1),(64,y1)],expected):
                self.assertEqual(view.getpixel(point),ink,(yaw,pitch,point))

    def test_right_limb_appears_viewer_left(self):
        data=design.fresh()
        data["base"]["right_arm"]="#e53945"
        data["base"]["left_arm"]="#39b65a"
        for model in ("classic","slim"):
            image=design.assemble(design.revise(data,model=model))
            view=render.render_view(image,model,width=100,height=160,scale=4,lighting=False)
            self.assertEqual(view.getpixel((26,72))[:3],(229,57,69))
            self.assertEqual(view.getpixel((74,72))[:3],(57,182,90))

    def test_outer_layer_is_visible_at_its_actual_location(self):
        image=fixture("classic",only_head=True)
        image.putpixel((43,11),(234,12,199,255))
        view=render.render_view(image,"classic",width=100,height=160,scale=4,lighting=False)
        self.assertEqual(view.getpixel((48,30))[:3],(234,12,199))

    def test_base_alpha_hole_rejected(self):
        image=design.assemble(design.fresh())
        image.putpixel((8,8),(0,0,0,0))
        self.assertFalse(design.validate_image(image,"classic")["ok"])

    def test_reference_review_uses_current_png_and_preserves_sources(self):
        import hashlib
        data=design.fresh()
        data["palette"]["foundation"]="#e23852"
        png=self.root/"skin.png"
        design.assemble(data).save(png)
        reference=self.root/"reference.png"
        Image.new("RGBA",(160,160),(10,170,70,255)).save(reference)
        before=(png.read_bytes(),reference.read_bytes())
        # A stale preview must never replace fresh texture rendering.
        Image.new("RGB",(360,480),"purple").save(self.root/"front.png")
        result=review.reference_review(png,reference,"classic",self.root)
        self.assertEqual(result["texture_sha256"],hashlib.sha256(before[0]).hexdigest())
        self.assertEqual(result["reference_sha256"],hashlib.sha256(before[1]).hexdigest())
        self.assertEqual(result["visual_likeness_review"],"pending")
        self.assertEqual(before,(png.read_bytes(),reference.read_bytes()))
        with Image.open(result["comparison"]) as output:
            self.assertEqual(output.getpixel((740,500)),(226,56,82))
            self.assertEqual(output.getpixel((250,400)),(10,170,70))

    def test_reference_review_protects_source_at_output_path(self):
        png=self.root/"skin.png"
        design.assemble(design.fresh()).save(png)
        source=self.root/"reference-review.png"
        Image.new("RGB",(20,20),"green").save(source)
        original=source.read_bytes()
        with self.assertRaises(ValueError):
            review.reference_review(png,source,"classic",self.root)
        self.assertEqual(source.read_bytes(),original)

    def test_build_preserves_reference_when_output_names_overlap(self):
        import skinmaker
        original=self.root/"skin.png"
        Image.new("RGB",(100,100),"green").save(original)
        before=original.read_bytes()
        with self.assertRaises(ValueError):
            skinmaker.build(design.fresh(),self.root,reference=original)
        self.assertEqual(original.read_bytes(),before)
        self.assertFalse((self.root/"design.json").exists())

    def test_slim_unused_arm_pixels_rejected(self):
        image=design.assemble(design.fresh(model="slim"))
        image.putpixel((54,20),(0,0,0,255))
        self.assertFalse(design.validate_image(image,"slim")["ok"])

    def test_custom_angle_cli_shows_requested_side_from_current_png(self):
        import hashlib
        import subprocess
        import sys
        png = self.root / "skin.png"
        texture = fixture("classic")
        texture.paste((255, 0, 0, 255), (16, 8, 24, 16))  # Wearer's left.
        texture.paste((0, 255, 0, 255), (0, 8, 8, 16))    # Wearer's right.
        texture.save(png)
        before = png.read_bytes()
        for yaw, expected in ((90, (232, 0, 0)), (-90, (0, 211, 0))):
            output = self.root / str(yaw)
            output.mkdir()
            Image.new("RGB", (360, 480), "purple").save(output / "custom-view.png")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("skinmaker.py")),
                                     "preview", str(png), "--yaw", str(yaw), "--pitch", "0",
                                     "--out", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["texture_sha256"], hashlib.sha256(before).hexdigest())
            with Image.open(report["view"]) as view:
                self.assertEqual(view.getpixel((180, 96))[:3], expected)
        self.assertEqual(png.read_bytes(), before)

    def test_custom_angle_rejects_invalid_angles_and_source_overwrite(self):
        png = self.root / "custom-view.png"
        fixture("classic").save(png)
        before = png.read_bytes()
        with self.assertRaises(ValueError):
            render.angle_preview(png, "classic", self.root, 33, 16)
        for yaw, pitch in ((float("nan"), 0), (0, 91), (0, float("inf"))):
            with self.assertRaises(ValueError):
                render.angle_preview(png, "classic", self.root / "invalid", yaw, pitch)
        self.assertEqual(png.read_bytes(), before)
        self.assertFalse((self.root / "invalid").exists())

    def test_fractional_outer_alpha_rejected(self):
        image=design.assemble(design.fresh())
        image.putpixel((40,8),(60,70,80,125))
        self.assertFalse(design.validate_image(image,"classic")["ok"])

    def test_non_png_and_wrong_dimensions_rejected(self):
        path=self.root/"wrong.png"
        Image.new("RGBA",(64,32)).save(path)
        self.assertFalse(design.validate_png(path,"classic")["ok"])
        Image.new("RGB",(64,64)).save(path,format="BMP")
        self.assertFalse(design.validate_png(path,"classic")["ok"])

    def test_paint_rejects_out_of_bounds(self):
        data=design.fresh()
        data["components"]=[{"id":"bad","paint":[{"target":"head.base.front","op":"rect","box":[7,0,2,2],"color":"#ff0000"}]}]
        with self.assertRaises(ValueError): design.assemble(data)

    def test_misspelled_keys_rejected_instead_of_ignored(self):
        for component in ({"id":"a","paints":[]},
                          {"id":"a","paint":[{"target":"head.base.front","op":"fill","colour":"#ff0000"}]},
                          {"id":"a","paint":[{"target":"head.base.front","op":"rect","box":[0,0,1,1],"color":"#ff0000","widht":2}]},
                          {"paint":[]}):
            data=design.fresh()
            data["components"]=[component]
            with self.assertRaises(ValueError): design.assemble(data)

    def test_transparent_base_paint_names_the_face(self):
        data=design.fresh()
        data["components"]=[{"id":"hole","paint":[{"target":"head.base.front","op":"points","points":[[1,1]],"color":"transparent"}]}]
        with self.assertRaisesRegex(ValueError,r"hole, head\.base\.front"): design.assemble(data)

    def test_design_symbols_are_shared_and_overridable(self):
        data=design.fresh()
        data["symbols"]={"A":"#ff0000","B":"#00ff00"}
        data["components"]=[{"id":"art","paint":[{"target":"head.base.front","op":"pixels","rows":["AB"],"map":{"B":"#0000ff"}}]}]
        image=design.assemble(data)
        self.assertEqual(image.getpixel((8,8)),(255,0,0,255))
        self.assertEqual(image.getpixel((9,8)),(0,0,255,255))

    def test_legacy_opaque_hat_cleared_and_real_hat_kept(self):
        image=fixture("classic",outer=True).crop((0,0,64,32))
        image.paste((0,0,0,255),(32,0,64,16))
        path=self.root/"legacy-solid-hat.png"
        image.save(path)
        out=design.assemble(design.import_skin(path))
        self.assertEqual(out.getpixel((40,8))[3],0)
        image.putpixel((33,0),(0,0,0,0))
        image.save(path)
        out=design.assemble(design.import_skin(path))
        self.assertEqual(out.getpixel((40,8)),(0,0,0,255))

    def test_diff_reports_face_local_changes(self):
        before=self.root/"before.png"
        after=self.root/"after.png"
        image=design.assemble(design.fresh())
        image.save(before)
        image.putpixel((8+3,8+5),(1,2,3,255))  # head.base.front at face-local (3,5)
        image.save(after)
        report=tiles.difference(before,after,"classic",self.root/"diff")
        self.assertEqual(report["changed_pixels"],1)
        self.assertEqual(report["faces"],{"head.base.front":{"pixels":1,"box":[3,5,1,1]}})
        self.assertTrue(Path(report["sheets"][0]).exists())

    def test_face_sheets_cover_requested_parts(self):
        png=self.root/"skin.png"
        fixture("slim",outer=True).save(png)
        result=tiles.face_sheets(png,"slim",self.root/"faces",("head","left_arm"))
        self.assertEqual([Path(p).name for p in result["sheets"]],["faces-head.png","faces-left_arm.png"])

    def test_preview_shows_both_three_quarter_sides(self):
        data=design.fresh()
        data["base"]["right_arm"]="#e53945"
        data["base"]["left_arm"]="#39b65a"
        png=self.root/"skin.png"
        design.assemble(data).save(png)
        render.previews(png,"classic",self.root)
        for name,near,far in (("three-quarter",(229,57,69),(57,182,90)),("three-quarter-left",(57,182,90),(229,57,69))):
            with Image.open(self.root/f"{name}.png") as view:
                colors={view.getpixel((x,240))[:3] for x in range(360)}
            # The arm nearest the camera is fully visible; exact shading varies by face.
            self.assertTrue(any(abs(c[0]-near[0])<40 and abs(c[1]-near[1])<40 for c in colors),name)

    def test_semantic_palette_revision_preserves_other_pixels(self):
        data=design.fresh()
        data["palette"]["jacket"]="#168c8b"
        data["base"]["body"]="jacket"
        before=np.array(design.assemble(data))
        after=np.array(design.assemble(design.revise(data,{"jacket":"#b83543"})))
        changed=np.any(before!=after,axis=2)
        allowed=np.zeros((64,64),dtype=bool)
        for x,y,w,h in CLASSIC["body.base"]: allowed[y:y+h,x:x+w]=True
        self.assertTrue(np.array_equal(changed,allowed))

    def test_model_conversion_preserves_non_arm_pixels(self):
        before=fixture("classic",outer=True)
        after=uv.convert_model(before,"classic","slim")
        for key,rects in CLASSIC.items():
            if "arm" not in key:
                for x,y,w,h in rects:
                    self.assertEqual(before.crop((x,y,x+w,y+h)).tobytes(),after.crop((x,y,x+w,y+h)).tobytes())
        self.assertTrue(design.validate_image(after,"slim")["ok"])

    def test_build_is_deterministic(self):
        data=design.fresh()
        self.assertEqual(design.assemble(data).tobytes(),design.assemble(copy.deepcopy(data)).tobytes())

    def test_import_roundtrip_both_models(self):
        for model in ("classic","slim"):
            image=fixture(model,outer=True)
            path=self.root/f"{model}.png"
            image.save(path)
            data=design.import_skin(path)
            self.assertEqual(data["model"],model)
            self.assertEqual(image.tobytes(),design.assemble(data).tobytes())

    def test_legacy_expansion_swaps_side_faces(self):
        image=fixture("classic").crop((0,0,64,32))
        path=self.root/"legacy.png"
        image.save(path)
        out=design.assemble(design.import_skin(path))
        self.assertEqual(out.getpixel((20,52)),image.getpixel((7,20)))
        self.assertEqual(out.getpixel((16,52)),image.getpixel((11,20)))
        self.assertTrue(design.validate_image(out,"classic")["ok"])

    def test_explicit_model_metadata_overrides_alpha_heuristic(self):
        image=fixture("slim",outer=True)
        # Some editors save opaque unused pixels, defeating alpha heuristics.
        image.putpixel((54,20),(99,77,55,255))
        path=self.root/"known-slim.png"
        image.save(path)
        data=design.import_skin(path,model="slim")
        restored=design.assemble(data)
        self.assertEqual(restored.getpixel((51,20)),image.getpixel((51,20)))
        self.assertEqual(restored.getpixel((54,20))[3],0)
        self.assertTrue(design.validate_image(restored,"slim")["ok"])

    def _pack(self,model="classic"):
        png=self.root/"skin.png"
        fixture(model).save(png)
        pack=self.root/"skin.mcpack"
        self.assertTrue(bedrock.package(png,pack,"Test skin",model)["ok"])
        return png,pack

    def test_packs_match_png_geometry_and_unique_ids(self):
        ids=[]
        for model in ("classic","slim"):
            png,pack=self._pack(model)
            check=bedrock.validate_pack(pack,model,png)
            self.assertTrue(check["ok"],check)
            ids.append(check["uuid"])
        self.assertEqual(len(set(ids)),2)

    def _tampered(self,filename,change):
        png,pack=self._pack()
        with zipfile.ZipFile(pack) as archive: files={n:archive.read(n) for n in archive.namelist()}
        value=json.loads(files[filename])
        change(value)
        files[filename]=json.dumps(value).encode()
        with zipfile.ZipFile(pack,"w") as archive:
            for n,b in files.items(): archive.writestr(n,b)
        return bedrock.validate_pack(pack,"classic",png)

    def test_duplicate_uuid_rejected(self):
        result=self._tampered("manifest.json",lambda x:x["modules"][0].update(uuid=x["header"]["uuid"]))
        self.assertFalse(result["ok"])

    def test_paid_skin_rejected(self):
        self.assertFalse(self._tampered("skins.json",lambda x:x["skins"][0].update(type="paid"))["ok"])

    def test_wrong_geometry_rejected(self):
        self.assertFalse(self._tampered("skins.json",lambda x:x["skins"][0].update(geometry="geometry.humanoid.customSlim"))["ok"])

    def test_missing_texture_rejected(self):
        self.assertFalse(self._tampered("skins.json",lambda x:x["skins"][0].update(texture="missing.png"))["ok"])

    def test_localization_mismatch_rejected(self):
        self.assertFalse(self._tampered("skins.json",lambda x:x.update(serialize_name="missing"))["ok"])

    def test_pack_exact_png_mismatch_rejected(self):
        png,pack=self._pack()
        other=self.root/"other.png"
        design.assemble(design.fresh()).save(other)
        self.assertFalse(bedrock.validate_pack(pack,"classic",other)["ok"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SkinTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    for model in ("classic","slim"):
        image=fixture(model)
        png=out/f"{model}-asymmetric-fixture.png"
        image.save(png)
        render.previews(png,model,out/model,f"{model.title()} UV orientation fixture")
    report={"ok":result.wasSuccessful(),"tests":result.testsRun,"failures":len(result.failures),
            "errors":len(result.errors),"in_game_test":"not performed",
            "fixture":"independently specified atlas rectangles and four unequal corner colors"}
    design.write(out/"selftest.json",report)
    return 0 if result.wasSuccessful() else 1


if __name__=="__main__":
    raise SystemExit(main())
