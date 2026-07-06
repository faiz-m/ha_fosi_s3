# Contributing

Thanks for your interest in improving the Fosi Audio S3 integration. This is a
small project — issues and pull requests are welcome.

## Development setup

The integration vendors the standalone `pyfosi` client library under
`custom_components/fosi_s3/pyfosi/` so it has no external dependencies. Tests run
against Home Assistant via `pytest-homeassistant-custom-component`.

```bash
# from the repo root
python3 -m pip install pytest pytest-homeassistant-custom-component
python3 -m pytest
```

If you change the vendored library, keep the copy in sync and verify it:

```bash
scripts/sync_pyfosi.sh          # copy source -> vendored
scripts/sync_pyfosi.sh --check  # fail if out of sync (run in CI)
```

## Pull requests

- Include tests for behaviour changes and keep the suite green.
- Keep the code lint-clean (`ruff check`).
- Keep changes focused; describe the user-visible effect in the PR.

## AI-assisted contributions

Using AI tools (Claude Code, Copilot, etc.) to help write a contribution is
fine. A few expectations so the project stays maintainable:

- **Disclose it.** Note in the PR that AI assistance was used.
- **Own what you submit.** You are responsible for understanding, testing, and
  standing behind every line — the same as hand-written code. "The AI wrote it"
  is not a substitute for review.
- **No unreviewed output.** Please don't open PRs or issues that are raw,
  untested AI output, and don't file AI-generated "security reports" without a
  verified, reproducible finding.

Contributions are judged on quality, not on how they were produced.
