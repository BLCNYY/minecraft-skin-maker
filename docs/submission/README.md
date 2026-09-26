# Directory submission materials

The plugin uses the same skin-making code in each host. `plugin.json` is the portable entry point. Platform manifests are in `.codex-plugin/`, `.claude-plugin/` and `.cursor-plugin/`.

- [Listing fields](listing.json): descriptions, source and support URLs, tags and starter prompts.
- [Reviewer test cases](test-cases.json): five positive and three negative scenarios with expected outcomes.
- [OG reference and result](../../README.md#og-example): public example and attribution.
- [Privacy](../../PRIVACY.md) and [usage terms](../../TERMS.md).

The OG demonstration contains only the reference and final result. The example artwork keeps its separate license. OpenAI's skills-only submission does not accept `interface.screenshots`, so the example is linked in the listing materials and README.

## Build release packages

```sh
python scripts/package_release.py --out dist
```

This creates a complete plugin ZIP, a standalone skill ZIP, a smaller SkillHub ZIP and SHA-256 checksums. The package builder uses an explicit file list, excludes environments and caches, and checks manifests and internal paths. It preserves all scripts, references, templates and masks required by the skill.

SkillHub's ZIP importer limits extracted content to 100 KB. Its package keeps every helper and test and links the two optional example designs at the matching GitHub release tag. The full examples remain in the repository and other ZIPs. The packager checks this size limit before writing the archive.

## Official submission routes

- OpenAI: [plugin submission](https://platform.openai.com/plugins), using Skills only when available to the publisher. [Requirements](https://developers.openai.com/plugins/deploy/submission).
- Claude: [directory submission](https://claude.ai/directory/manage/new). [Publisher announcement](https://claude.com/blog/build-plugins-for-claude).
- Cursor: [marketplace submission](https://cursor.com/marketplace/publish). [Manifest and review requirements](https://cursor.com/docs/reference/plugins).

An installable package, a submitted listing and an approved public listing are separate states. Record the actual portal receipt before claiming a submission or approval. Availability and review requirements can vary by account.
