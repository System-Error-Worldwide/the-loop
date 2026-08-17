# Contributing

SYSTEM ERROR'S THE LOOP accepts focused contributions that preserve its cross-harness behavior, safety boundaries and provenance rules.

## Before opening a pull request

1. Read [PROVENANCE.md](PROVENANCE.md) and the [public/private boundary](docs/provenance/public-private-boundary.md).
2. Do not copy private, vendor or community skill text without a compatible licence and an approved provenance record.
3. Keep portable behavior independent of Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness. Harness-specific behavior belongs in a thin adapter.
4. Use synthetic fixtures. Never include credentials, customer data, private infrastructure or incident history.
5. Run:

   ```sh
   python3 scripts/validate_repository.py
   python3 -m unittest discover -s tests -p 'test_*.py'
   ```

## Pull requests

Keep each pull request to one reviewable change. Explain the capability, evidence,
provenance classification and any harness-specific limitations. A contribution is not
ready while tests fail or its provenance record is missing.

By contributing, you confirm that you have the right to submit the work and agree that it is licensed under this repository's [MIT License](LICENSE).

## Support boundary

Use GitHub Issues for reproducible bugs and bounded feature proposals. Do not post vulnerabilities, credentials or private operational data in a public issue. Follow [SECURITY.md](SECURITY.md) for security reports.
