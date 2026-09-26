"""Local reference comparison using fresh renders of the delivered skin PNG."""
import hashlib
import itertools
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from design import validate_png
from render import bounds, camera, render_view


def _head_detail(view, model, yaw, pitch):
    lo, hi = bounds("head", model, "outer")
    points = np.array(list(itertools.product(*zip(lo, hi)))) - np.array([0,16,0])
    right, up, _ = camera(yaw, pitch)
    xs = view.width/2+(points@right)*12
    ys = view.height/2-(points@up)*12
    box = (max(0,math.floor(xs.min())-5),max(0,math.floor(ys.min())-5),
           min(view.width,math.ceil(xs.max())+5),min(view.height,math.ceil(ys.max())+5))
    return view.crop(box)


def reference_review(png, reference, model, destination, title="Reference review"):
    png, reference, destination = Path(png), Path(reference), Path(destination)
    result_path = destination/"reference-review.png"
    if result_path.resolve() in (png.resolve(),reference.resolve()):
        raise ValueError("Reference review output must differ from both source images")
    check = validate_png(png,model)
    if not check["ok"]:
        raise ValueError("Invalid skin for reference review: " + "; ".join(check["errors"]))
    with Image.open(reference) as source:
        source.load()
        original = ImageOps.exif_transpose(source).convert("RGBA")
    with Image.open(png) as source:
        texture = source.convert("RGBA")
    # Render now, so a previous preview cannot be mistaken for the current skin.
    front = render_view(texture,model)
    angled = render_view(texture,model,-33,16)
    small = render_view(texture,model,width=120,height=160,scale=4)
    canvas = Image.new("RGB",(1400,880),"#eef1f4")
    draw = ImageDraw.Draw(canvas)
    heading = ImageFont.load_default(size=27)
    label = ImageFont.load_default(size=16)
    title = title if len(title)<70 else title[:67]+"..."
    draw.text((25,22),title,fill="#1c2b38",font=heading)
    draw.text((25,61),"Reference, full skin, enlarged head details and a small view",fill="#526675",font=label)
    draw.text((25,108),"REFERENCE",fill="#526675",font=label)
    fitted = ImageOps.contain(original,(525,690),Image.Resampling.LANCZOS)
    canvas.paste(fitted,(25+(525-fitted.width)//2,145+(690-fitted.height)//2),fitted)
    draw.text((740,140),"EXPORTED SKIN",anchor="mm",fill="#526675",font=label)
    canvas.paste(front.convert("RGB"),(560,220))
    for image, x, text in ((front,960,"FACE"),(angled,1175,"HAIR AND LAYERS")):
        yaw,pitch=(0,0) if text=="FACE" else (-33,16)
        detail=ImageOps.contain(_head_detail(image,model,yaw,pitch),(200,240),Image.Resampling.NEAREST)
        draw.text((x+100,140),text,anchor="mm",fill="#526675",font=label)
        canvas.paste(detail.convert("RGB"),(x+(200-detail.width)//2,180+(240-detail.height)//2))
    draw.text((1165,504),"SMALL VIEW",anchor="mm",fill="#526675",font=label)
    canvas.paste(small.convert("RGB"),(1105,545))
    draw.text((25,852),"Compare distinguishing features, expression, hair shape and material shading.",fill="#526675",font=label)
    destination.mkdir(parents=True,exist_ok=True)
    canvas.save(result_path)
    return {"comparison":str(result_path),"model":model,
            "texture_sha256":hashlib.sha256(png.read_bytes()).hexdigest(),
            "reference_sha256":hashlib.sha256(reference.read_bytes()).hexdigest(),
            "visual_likeness_review":"pending", "in_game_tested":False}
