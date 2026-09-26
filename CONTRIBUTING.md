# Contributing

Keep the image-or-text workflow usable without Minecraft-specific setup questions. Preserve exported PNG compatibility, editable designs and previews sampled from the final texture.

## Check a change

Install `skills/minecraft-skin-maker/requirements.txt`, then run:

```sh
python skills/minecraft-skin-maker/scripts/selftest.py --out work/checks
```

For visual changes, render the affected design and inspect the exported previews against the reference. Describe the visible change and any remaining compromises in the pull request. Automated format checks and in-game testing should be reported separately.

Use original or appropriately licensed references for new examples. The repository owner's OG artwork has separate terms under `examples/og/LICENSE.md`.
