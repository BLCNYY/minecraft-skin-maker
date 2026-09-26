# Technical guide

[← Back to the README](../README.md)

## Contents

- [Other installation options](#other-installation-options)
- [Requirements and compatibility](#requirements-and-compatibility)
- [Outputs and importing](#outputs-and-importing)
- [How it works](#how-it-works)
- [Development](#development)
- [Current limits](#current-limits)

## Other installation options

The [README](../README.md#install) shows the shared installer. It supports Codex, Claude Code, Cursor and other agent hosts. Node.js is needed only for that installer; the skill's helpers use Python.

### Plugins

The repository includes plugin manifests for Codex, Claude Code and Cursor, plus a portable Agent Plugins manifest. The [plugin ZIP](https://github.com/BLCNYY/minecraft-skin-maker/releases) includes the complete skill and its Python helpers. Public directory listings depend on each platform's review; this repository is also available through the shared installer.

For Claude Code, add this repository as a marketplace and install the plugin:

```sh
claude plugin marketplace add BLCNYY/minecraft-skin-maker
claude plugin install minecraft-skin-maker@blcnyy-minecraft-skins
```

Its namespaced skill is `/minecraft-skin-maker:minecraft-skin-maker`.

For a local Cursor CLI installation, clone or extract the plugin and start a session with `agent --plugin-dir /path/to/minecraft-skin-maker`. The shared installer also supports Cursor.

See the [submission materials](submission/README.md), [privacy policy](../PRIVACY.md) and [usage terms](../TERMS.md).

### Codex shortcut

Paste this into Codex:

```text
Use $skill-installer to install https://github.com/BLCNYY/minecraft-skin-maker/tree/main/skills/minecraft-skin-maker
```

### Manual installation or another host

Copy the complete `skills/minecraft-skin-maker` folder into your host's skills directory. Keep its scripts, references and assets together. For example:

| Host | Personal skill folder | Explicit invocation |
| --- | --- | --- |
| Codex | `~/.codex/skills/minecraft-skin-maker/` | `$minecraft-skin-maker` |
| Claude Code | `~/.claude/skills/minecraft-skin-maker/` | `/minecraft-skin-maker` |

See [Claude Code's skill documentation](https://code.claude.com/docs/en/skills) for its discovery and invocation rules. Other hosts may use different locations or require a new session after installation.

An agent without native skill discovery can read [SKILL.md](../skills/minecraft-skin-maker/SKILL.md) directly from a local clone and follow the workflow, provided it has the capabilities below. A [downloadable skill ZIP](https://github.com/BLCNYY/minecraft-skin-maker/releases) is also available.

## Requirements and compatibility

The complete workflow needs an agent that can:

- Read the skill's instructions and supporting files, and write output files.
- Run Python 3.10+ with Pillow and NumPy, setting up dependencies when needed.
- Inspect reference images and generated previews. Text requests also include a visual review of the output.

The chosen model and tools supply image interpretation and creative decisions. Generation uses that agent's normal account and usage limits. The Python helpers assemble and render locally without a separate image-generation API. `agents/openai.yaml` supplies optional Codex interface metadata; the shared workflow and helpers work independently of that file.

**Validation status:** the complete creative workflow has been tested in Codex. The shared installer has been checked in isolated project directories for Claude Code, Codex and Cursor. Cursor CLI also discovers the packaged plugin's skill and reads its supporting files. Complete generation workflows have not yet been tested in other hosts.

The portable manifest passes the Agent Plugins schema; the Codex package and Claude Code plugin and marketplace pass their validators. All 28 helper tests pass from the extracted plugin ZIP. The Python helpers pass checks on macOS, Linux and Windows. A chat environment with no file execution or image inspection cannot complete this workflow on its own.

## Outputs and importing

- A **64×64 skin PNG** for Minecraft.
- Front, back and angled **previews rendered from that PNG**.
- A companion **Bedrock `.mcpack`** by default.
- An **editable design** for later changes.
- Import instructions and automated file checks.
- A reference comparison and visual inspection record when using an image.

Technical choices are automatic. You can volunteer preferences such as Slim arms or Java-only export. Revisions can be simple: “Make the hoodie red and keep everything else.”

- **Java:** In the Minecraft Launcher, open Java Edition → Skins → New Skin. Choose the exported PNG and the model named in its import notes. The OG example uses **Classic/Wide**.
- **Bedrock on Windows or mobile:** Open the `.mcpack` with Minecraft and choose the imported skin under Dressing Room → Classic Skins. The generated import notes include a PNG fallback.
- **Consoles:** Xbox, PlayStation and Switch do not officially support importing arbitrary custom skin files.

See [format and import references](../skills/minecraft-skin-maker/references/formats-and-import.md) for sources and platform details.

### OG example files

The skin keeps the orange fringe, blue and green eyes, lavender hoodie cords and white sleeve bands. Plain dark trousers and shoes complete the unseen lower half.

[Front, back and angled preview](../examples/og/preview.png) · [Face comparison](../examples/og/reference-review.png) · [Skin PNG](../examples/og/skin.png) · [Bedrock pack](../examples/og/skin.mcpack) · [Editable design](../examples/og/design.json)

The character example has [separate artwork terms](../examples/og/LICENSE.md).

## How it works

1. Your agent reads the reference or description and records identifying features and any assumptions.
2. It writes an editable design with named colors and components for the face, hair and clothing.
3. Python assembles the skin, validates its texture layout and builds previews and a Bedrock pack.
4. Your agent compares the previews with the reference, corrects visible mismatches and inspects the final export.

Image interpretation and creative design happen in the agent. The Python tools assemble a supplied design deterministically. Given the same design, the skin PNG is reproducible; Bedrock pack identifiers are regenerated for each build.

## Development

Run these commands from the repository root.

Install the helper dependencies:

```sh
python -m pip install -r skills/minecraft-skin-maker/requirements.txt
```

Build the included OG example:

```sh
python skills/minecraft-skin-maker/scripts/skinmaker.py build examples/og/design.json --reference examples/og/reference.png --out work/og
```

Run the checks:

```sh
python skills/minecraft-skin-maker/scripts/selftest.py --out work/checks
```

The suite has 28 checks covering Classic/Slim texture layouts, face orientation, transparency, imports, revisions, preview sources and Bedrock packages. CI also rebuilds the OG example and checks that its PNG matches the committed skin.

Build the plugin, standalone skill and SkillHub ZIPs, with checksums:

```sh
python scripts/package_release.py --out dist
```

More detail: [skill workflow](../skills/minecraft-skin-maker/SKILL.md), [design format](../skills/minecraft-skin-maker/references/design-format.md), [likeness review](../skills/minecraft-skin-maker/references/likeness-and-pixel-art.md).

## Current limits

This is an early public release. The OG output has passed file checks and visual inspection; an actual in-game import has not been verified. Minecraft's standard block model and small pixel grid simplify curved hairstyles and expressions. Unseen parts of a character require interpretation.

The helper supports standard player skins and outer layers. Custom 3D geometry, functional capes, high-resolution skins and automatic account uploads are outside its scope.

To report a problem, [open an issue](https://github.com/BLCNYY/minecraft-skin-maker/issues) with your prompt, expected result and generated preview. Include a reference image only if you are comfortable sharing it publicly.
