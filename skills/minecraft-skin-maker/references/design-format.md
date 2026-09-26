# Editable design format

Codex interprets the request or visible reference; the Python tools assemble its decisions. They do not contain an image-recognition or text-generation model. Write a design for the actual input. The blank template and examples are coordinate aids, not a fixed character preset.

## Start

`skinmaker.py init design.json --name "Character name"` creates all required base fills. Edit its palette, base colors and named components. Read `assets/classic-uv.json` or `assets/slim-uv.json` only if exact atlas positions are needed; drawing operations use face-local coordinates.

```json
{
  "schema_version": 1,
  "name": "Copper explorer",
  "model": "classic",
  "canvas_model": "classic",
  "palette": {
    "skin": "#a87755", "jacket": "#267b80", "jacket_shadow": "#205c66",
    "trousers": "#30354d", "hair": "#352c32", "eye": "#161923"
  },
  "base": {
    "head": "skin", "body": "jacket", "right_arm": "jacket",
    "left_arm": "jacket", "right_leg": "trousers", "left_leg": "trousers"
  },
  "components": [
    {"id": "hair", "paint": [
      {"target": ["head.base.top", "head.base.back"], "op": "fill", "color": "hair"},
      {"target": "head.base.front", "op": "rect", "box": [0, 0, 8, 2], "color": "hair"}
    ]},
    {"id": "eyes", "paint": [
      {"target": "head.base.front", "op": "points", "points": [[2, 4], [5, 4]], "color": "eye"}
    ]},
    {"id": "jacket-cuff", "paint": [
      {"target": "right_arm.outer.front", "op": "rect", "box": [0, 8, 4, 1], "color": "jacket_shadow"}
    ]}
  ],
  "notes": ["The unseen back continues the jacket color."]
}
```

This snippet illustrates the format. Add deliberate face, hair, clothing, boot, seam and outer-layer details to finish an actual design.

## Coordinates and operations

Targets are `part.layer.face` or lists of those strings. Parts: `head`, `body`, `right_arm`, `left_arm`, `right_leg`, `left_leg`. Layers: `base`, `outer`. Faces: `front`, `back`, `left`, `right`, `top`, `bottom`. Left and right are always the wearer's side. The wearer's right appears on the viewer's left in a front view. Face `(0,0)` is the upper-left pixel in the atlas tile, not a world coordinate. On top and bottom tiles, row zero is the back edge; column zero is the wearer's right edge. Side tiles run around the box: the right face's last column meets the front; the left face's first column meets the front. Back tiles reverse the front's world x direction.

Sizes: head faces 8×8; body front/back 8×12, sides 4×12, top/bottom 8×4; leg front/back/sides 4×12, top/bottom 4×4. Classic arms match legs. Slim arm front/back 3×12, sides 4×12, top/bottom 3×4. Outer tiles have the same pixel dimensions as their base tile.

Components run in order and must have unique IDs. Operations replace pixels (including alpha); they do not alpha-blend into existing pixels.

- `fill`, `color`: cover the whole target face.
- `rect`, `box: [x,y,width,height]`, `color`: integer pixel rectangle.
- `points`, `points: [[x,y], ...]`, `color`: individual pixels.
- `line`, `points`, `color`, optional `width` (default 1).
- `polygon`, `points`, `color`: filled polygon.
- `pixels`, `at: [x,y]`, `rows: [".AB.", "ABBA"]`, `map: {"A":"hair","B":"#987865"}`: hand-authored pixel art. A dot preserves the previous pixel. Map another symbol to `transparent` to erase outer pixels. All rows must fit the face.

Colors are named palette keys or `#RRGGBB`/`#RRGGBBAA`. Base alpha must equal 255. Use alpha 0 or 255 for outer layers so the same skin behaves consistently in Java and Bedrock. No random noise, automatic gradients or hidden styling is added by the assembler.

## Revision behavior

Use specific palette keys such as `jacket`, `jacket_light`, `jacket_shadow`, `scarf`, `hair`, `hair_light`. A jacket edit should update only jacket keys or jacket components, even if another garment currently has the same color. Keep the previous design and outputs in a separate directory. Compare actual pixel differences and check they stay inside the intended faces or materials.

`revise --model slim` retains `canvas_model` and resamples only arm face widths using nearest-neighbor sampling. All non-arm pixels remain exact. Moving side and back tiles is necessary to repack the arm net. Width reduction can lose a pixel of small motifs: inspect and refine affected arms. Operations remain in `canvas_model` coordinates for future edits.

`import` embeds the source PNG inside JSON, so designs remain portable. Add named components to make targeted changes. Alpha is normalized and unused regions cleared; reported repairs should be disclosed when material. Model metadata from an existing design or known source takes priority over the PNG heuristic. An unmarked 64×64 PNG alone can be ambiguous. Legacy 64×32 PNGs expand to Classic with mirrored left limbs.

Keep creative assumptions in `notes`. For reference work, add a `reference_brief` object with `identity_anchors`, `orientation`, `expression`, `materials` and `unseen_areas` as useful. These are agent-written observations; the helper preserves them without assigning a likeness score. Follow [likeness-and-pixel-art.md](likeness-and-pixel-art.md) for translating and reviewing them. Keep source images local and outside Bedrock packs. Preserve originals when useful for subsequent edits.
