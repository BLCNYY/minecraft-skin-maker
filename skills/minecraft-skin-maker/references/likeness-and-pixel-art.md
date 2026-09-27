# Likeness and pixel-art review

Use this guide when translating a reference or when a skin captures the colors but still feels unlike the character. Keep creative choices internal; complete a first result with the normal automatic defaults.

## Read the character before drawing

Save a short `reference_brief` in the editable design: recognizable features, orientation, expression, material treatment, and assumptions for unseen areas. Prioritize the features that distinguish this subject. Examples include the direction and depth of a fringe, unequal eye colors, a hood shape, a stripe's position, or a distinctive collar. Match their relative sizes and placement as well as their colors.

Record left/right explicitly for asymmetric features. A tilted portrait may make one eye look smaller; decide which differences describe the character and which come from perspective. Keep face proportions coherent in the straight-on skin. Choose quiet, consistent details for unseen trousers, shoes or the back, and mention substantial inventions briefly after delivery.

## Hair and expression

Resolve the head before decorating the outfit. An 8×8 front face has little room: reserve pixels for the eyes and expression, then shape the hairline around them.

- Follow the reference's part, sweep and lock groupings. Use contiguous bands of color that follow those shapes; make a highlight describe a lock or a broad lit area.
- Use selected outer-layer patches for fringe, temples and overlapping locks. Break exposed edges into purposeful steps. The underlying cuboid still limits the silhouette; suggest the character's volume with placement and shading inside those limits.
- Place hair highlights and shadows consistently across front, sides, top and back. Avoid a rectangular highlight cap, long straight helmet borders, or random alternating pixels unless the reference calls for them.
- Keep distinctive eyes visible and correctly oriented. Use a deliberate arrangement of sclera, iris and pupil at the available resolution. Strong brows, large noses or very dark mouth pixels can change the apparent age or expression.
- For a gentle face, keep skin shadows close to the base color. Test a small, low-contrast mouth or a slight asymmetry when that helps express the reference. Judge the rendered face: a pixel that reads as a moustache, scowl or nose should be repositioned or softened. A mouth is optional if the face reads better without it.

## Materials and clothing

Start each material with a base tone, a nearby shadow and a nearby highlight. Add tones when a visible feature or surface needs them. Smooth cloth benefits from broad uninterrupted areas. Place shading at seams, hems, folds, under a hood, and where sleeves join the torso. Keep lighting coherent around the body.

Maintain the reference's contrast hierarchy: a dark hoodie can remain mostly dark while white bands and colored cords carry the detail. Draw folds with connected shapes or a few pixels near a seam. Scattered light/dark squares can turn plain fabric into apparent camouflage, armor or worn stone. Use that texture only when it belongs to the subject.

Give each distinctive construction detail its proper shape. A hood opening should wrap around the neck; drawstrings should hang from their attachment points; a zipper should continue through the garment; sleeve bands should align around every side. Put raised rims, cords, cuffs and hair on the outer layer selectively. Large flat outer panels can add unwanted bulk.

## Review the reference and the rendered skin together

For an image request, build with `--reference <image>` and open `reference-review.png`. This locally arranges the original image beside an exact-texture render, enlarged front/angled head views, and a small full-body view. It adds no likeness score and does not modify the reference or the skin.

Compare the result at both enlarged and small display sizes:

1. **Identity:** Are the subject's distinguishing features present, on the correct sides, and given enough visual emphasis?
2. **Head:** Does the fringe have the intended direction and overlap? Do the eyes and expression read correctly? Are outer-layer blocks helping the hair shape?
3. **Materials:** Does the garment still read as the reference's fabric or armor? Do highlights describe form? Is unnecessary noise competing with the identifying details?
4. **Construction:** Do collars, hood, seams, bands, pockets and cords connect logically across faces and layers?
5. **Unknown areas:** Do the invented parts support the visible design without introducing a competing theme?

Also open `preview.png` for the back and both three-quarter views. Correct concrete mismatches in the editable design and rebuild. If comparing against an earlier preview, use the same view and comparable display size. State the specific improvements and remaining compromises; automated format checks do not establish visual likeness.

Record the actual final inspection in `visual-inspection.md`, with the exported PNG's SHA-256 and the features checked. Keep the automated validation report distinct. A reference review marked pending requires the agent to open the images and make the visual judgment.
