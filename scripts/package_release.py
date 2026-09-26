#!/usr/bin/env python3
"""Build complete, reproducible plugin and standalone-skill archives."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'minecraft-skin-maker'
BASE = 'https://github.com/BLCNYY/minecraft-skin-maker'
SKILL = ROOT / 'skills' / NAME
EXCLUDED = {'__pycache__', '.venv', 'venv', 'node_modules', '.git', 'work', 'dist'}
EXTENSIONS = {'.md', '.py', '.json', '.yaml', '.yml', '.txt', '.png'}


def skill_files() -> list[Path]:
    result = []
    for path in sorted(SKILL.rglob('*')):
        rel = path.relative_to(SKILL)
        if any(part in EXCLUDED for part in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlinks are not included in releases: {rel}')
        if not path.is_file() or path.suffix in {'.pyc', '.pyo'}:
            continue
        if path.name == '.DS_Store':
            continue
        if path.suffix not in EXTENSIONS and path.name != 'LICENSE':
            raise ValueError(f'Review unexpected skill file before packaging: {rel}')
        result.append(path)
    for required in ['SKILL.md', 'requirements.txt', 'LICENSE', 'scripts/skinmaker.py',
                     'scripts/render.py', 'scripts/uv.py', 'scripts/design.py',
                     'scripts/review.py', 'scripts/bedrock.py', 'references/design-format.md']:
        if SKILL / required not in result:
            raise ValueError(f'Missing required skill file: {required}')
    return result


def validate_manifests() -> str:
    manifests = [ROOT / 'plugin.json'] + [ROOT / f'.{host}-plugin/plugin.json' for host in ('codex', 'claude', 'cursor')]
    values = [json.loads(p.read_text(encoding='utf-8')) for p in manifests]
    version = values[0]['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version):
        raise ValueError('Use a semantic release version')
    for path, value in zip(manifests, values):
        if value.get('name') != NAME or value.get('version') != version:
            raise ValueError(f'Manifest identity/version mismatch: {path.name}')
        for field in ('description', 'author', 'homepage', 'repository', 'license'):
            if not value.get(field):
                raise ValueError(f'Missing {field} in {path}')
        if 'mcpServers' in value or 'apps' in value or 'hooks' in value:
            raise ValueError('This release contains skills only')
    interface = values[1]['interface']
    if 'screenshots' in interface:
        raise ValueError('OpenAI skills-only packages exclude interface.screenshots')
    for key in ('logo', 'composerIcon'):
        asset = (ROOT / interface[key]).resolve()
        if not asset.is_relative_to(ROOT) or not asset.is_file():
            raise ValueError(f'Missing or escaping asset: {key}')
    marketplace = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
    entry = marketplace['plugins'][0]
    if entry['name'] != NAME or entry['source'] != './' or entry['version'] != version:
        raise ValueError('Claude marketplace does not resolve this release')
    return version


def write_archive(destination: Path, entries: dict[str, bytes]) -> dict:
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ValueError(f'Archive verification failed: {destination}')
        for name, data in entries.items():
            if archive.read(name) != data:
                raise ValueError(f'Archive bytes changed: {name}')
    return {'file': destination.name, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'bytes': destination.stat().st_size, 'files': len(entries)}


def skillhub_files(skill: dict[str, bytes], version: str) -> dict[str, bytes]:
    """Fit SkillHub's 100 KB import limit without removing executable helpers."""
    optional = {f'{NAME}/assets/examples/{name}.json' for name in ('field-botanist', 'lunar-courier')}
    if not optional.issubset(skill):
        raise ValueError('Review the example list before building the SkillHub package')
    result = {name: data for name, data in skill.items() if name not in optional and not name.endswith('.png')}
    path = f'{NAME}/SKILL.md'
    instruction = '`assets/examples/` contains two complete designs to illustrate component organization; design each new character from its own input.'
    text = result[path].decode('utf-8').replace('\r\n', '\n')
    if text.count(instruction) != 1:
        raise ValueError('Review the example reference before building the SkillHub package')
    examples = f'{BASE}/tree/v{version}/skills/{NAME}/assets/examples'
    replacement = f'Optional [example designs]({examples}) illustrate component organization. They are hosted on GitHub to keep this directory package small; design each new character from its own input.'
    text = text.replace(instruction, replacement)
    setup_marker = 'Exact commands:\n\n'
    if text.count(setup_marker) != 1:
        raise ValueError('Review the helper setup instructions before packaging')
    setup = ('Exact commands:\n\n'
             'For this SkillHub directory package, first regenerate its PNG coordinate guides and masks from the bundled code:\n\n'
             '```sh\n"$PY" "$SKILL_DIR/scripts/skinmaker.py" templates --out "$SKILL_DIR/assets"\n```\n\n'
             'This creates the same coordinate aids as the full package; SkillHub accepts only text support files. Then create or revise the skin:\n\n')
    result[path] = text.replace(setup_marker, setup).encode('utf-8')
    if sum(map(len, result.values())) > 100_000:
        raise ValueError('The complete runtime exceeds SkillHub\'s upload size limit')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    version = validate_manifests()
    args.out.mkdir(parents=True, exist_ok=True)
    sources = skill_files()
    # Only these root files and the complete skill directory enter the plugin.
    roots = ['plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json',
             '.claude-plugin/marketplace.json', '.cursor-plugin/plugin.json',
             'LICENSE', 'PRIVACY.md', 'TERMS.md', 'assets/icon.png', 'assets/icon.svg']
    plugin = {f'{NAME}/{name}': (ROOT / name).read_bytes() for name in roots}
    for path in sources:
        plugin[f'{NAME}/{path.relative_to(ROOT).as_posix()}'] = path.read_bytes()
    # The public example retains its separate artwork terms on GitHub.
    # Make README links usable after extraction without shipping that artwork.
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    readme = re.sub(r'(?<=[(])((?:examples|docs)/[^)]+)', lambda m: BASE + '/blob/main/' + m[1], readme)
    readme = readme.replace('src="examples/', 'src="https://raw.githubusercontent.com/BLCNYY/minecraft-skin-maker/main/examples/')
    readme = readme.replace('](CONTRIBUTING.md)', '](' + BASE + '/blob/main/CONTRIBUTING.md)')
    plugin[f'{NAME}/README.md'] = readme.encode()
    terms = plugin[f'{NAME}/TERMS.md'].decode().replace('](examples/og/LICENSE.md)', '](' + BASE + '/blob/main/examples/og/LICENSE.md)')
    plugin[f'{NAME}/TERMS.md'] = terms.encode()
    skill = {f'{NAME}/{path.relative_to(SKILL).as_posix()}': path.read_bytes() for path in sources}
    releases = [write_archive(args.out / f'{NAME}-plugin.zip', plugin),
                write_archive(args.out / f'{NAME}.zip', skill),
                write_archive(args.out / f'{NAME}-skillhub.zip', skillhub_files(skill, version))]
    (args.out / 'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in releases))
    report = {'name': NAME, 'version': version, 'archives': releases}
    (args.out / 'package-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
