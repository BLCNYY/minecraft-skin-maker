# Minecraft formats and import

Checked 2026-09-26. Recheck official guidance when a user's device or Minecraft update makes these instructions uncertain.

## Bedrock packaging

Microsoft's [skin-pack guide](https://learn.microsoft.com/en-us/minecraft/creator/documents/packagingaskinpack) specifies root-level `manifest.json`, `skins.json` and PNG textures, plus `texts/en_US.lang` and `texts/languages.json`. Use two distinct UUIDs and a `skin_pack` module. This helper emits manifest format 2, following the newer [Introduction to Skin Packs](https://learn.microsoft.com/en-us/minecraft/creator/documents/skinpack) (updated 2025-07-31) and [skin-pack JSON reference](https://github.com/MicrosoftDocs/minecraft-creator/blob/main/creator/Reference/Content/SkinPacksReference/SkinPackJSONReference.md). The older packaging guide shows format 1; the validator accepts both.

`geometry.humanoid.custom` selects Classic; `geometry.humanoid.customSlim` selects Slim. Each skin is `type: free`. The pack serialization/localization key is unique. The language file supplies `pack.name`, `skinpack.<pack-key>` and `skin.<pack-key>.<skin-key>`. `languages.json` lists `en_US`. Localized additional files are optional and must agree with that list. The archive is ZIP with `.mcpack` extension and no enclosing folder. Each new package gets fresh header/module UUIDs, including revisions, so it imports as a separate pack.

## Short import text

- **Java, including macOS:** Launcher → Java Edition → Skins → New Skin → browse to the PNG → select the matching Classic/Wide or Slim model → Save & Use. [Official skin guide](https://www.minecraft.net/en-us/article/what-is-minecraft-skin)
- **Bedrock on Windows, Android or iOS:** Open the `.mcpack` with Minecraft and select it in Dressing Room → Classic Skins. [Official sample and import instructions](https://github.com/microsoft/minecraft-samples/blob/main/skinpack/README.md). If file association is unavailable, import the PNG through Classic Skins → Owned/Import → Choose New Skin; match the arm thumbnail. That PNG route is documented in [Mojang's release notes](https://feedback.minecraft.net/hc/en-us/articles/360033538652-Minecraft-Beta-1-13-0-15-Xbox-One-Windows-10-Android); menu labels and the file picker vary by release.
- **Xbox, PlayStation, Switch:** Official custom-file imports are unavailable. A generated pack does not bypass that platform restriction. Bedrock custom skins do not automatically synchronize between devices. [Official Character Creator FAQ](https://www.minecraft.net/en-us/article/character-creator-faq)

The FAQ includes older product names but remains the official statement consulted on the date above. Do not claim a live game import based on it. The helper produces files; it does not access the user's Minecraft account or install Minecraft.

## UV and rendering convention

Modern player skins have 64×64 pixels, six cuboids and two layers. See `assets/*-uv.json` for each exact rectangle and `*-mask.png` for alpha checks. Independent orientation checks use asymmetric corner pixels and a separately specified atlas fixture. Geometry and face orientation were cross-checked with the primary [skinview3d model implementation](https://github.com/bs-community/skinview3d/blob/master/src/model.ts), including its reversed bottom-UV vertex assignment. Our renderer is independently written and samples the delivered PNG directly.

The default preview is a stationary, orthographic player model. Head outer surfaces extend 0.5 model units per side; other outer surfaces extend 0.25. It renders both sides of transparent outer surfaces with depth sorting. Game lighting, animation, capes, held objects, armor, and shader modifications are outside this preview.

Separate three kinds of evidence: automated texture/pack checks; a human/agent viewing the exported previews; actual import and appearance in Minecraft. Record only the checks performed.
