# viavitae-brand

[![CI](https://github.com/Via-Vitae/viavitae-brand/actions/workflows/ci.yml/badge.svg)](https://github.com/Via-Vitae/viavitae-brand/actions/workflows/ci.yml)
[![Compliance](https://github.com/Via-Vitae/viavitae-brand/actions/workflows/compliance-check.yml/badge.svg)](https://github.com/Via-Vitae/viavitae-brand/actions/workflows/compliance-check.yml)
[![CodeQL](https://github.com/Via-Vitae/viavitae-brand/actions/workflows/codeql.yml/badge.svg)](https://github.com/Via-Vitae/viavitae-brand/actions/workflows/codeql.yml)
[![Licence](https://img.shields.io/badge/licence-Proprietary-0E1B3D?labelColor=F7F4EC)](LICENSE)
[![EU hosted](https://img.shields.io/badge/hosted-EU-0E1B3D?labelColor=F7F4EC)](SECURITY.md)

> W3C design tokens, brand assets, validation tooling and build exports for the ViaVitae
> design system.

`viavitae-brand` is the single source of truth for ViaVitae's visual identity: design
tokens (colours, typography, spacing, breakpoints, elevation, radius, icons and motion),
SVG logo masters, raster export pipeline, liturgical imagery and the Python tooling that
validates and builds derived artefacts (CSS custom properties, Figma Variables JSON,
raster logos, favicons, OG cards, WOFF2 font subsets).

ViaVitae builds church-vertical websites, e-commerce and a marketplace for an EU pilot
in Lithuania, on self-hosted Proxmox infrastructure. Personal data stays in the EEA.

---

## Table of Contents

- [Repository purpose](#repository-purpose)
- [Design tokens](#design-tokens)
- [Brand assets](#brand-assets)
- [Build and validation tooling](#build-and-validation-tooling)
- [Repository layout](#repository-layout)
- [Development workflow](#development-workflow)
- [Quality gates](#quality-gates)
- [Security and compliance](#security-and-compliance)
- [Documentation](#documentation)
- [Licence](#licence)

---

## Repository purpose

This repository contains **sources, not derived artefacts** (with two deliberate
exceptions: `build/css/tokens.css` and `build/figma-tokens/tokens.json` are committed so
consumers can import them directly). The build pipeline in
`.github/workflows/ci.yml` and the Python scripts under `tools/` validate every token,
every SVG master and every cross-file invariant on each push.

The governing rule: **SOURCES ARE COMMITTED, DERIVED ARTEFACTS ARE NOT.** An SVG master
is a source. A PNG rasterised from it is derived. A committed derived artefact is a
second copy of a value that can disagree with the first, and the disagreement is always
found by the consumer downloading the stale one.

## Design tokens

Design tokens follow the [W3C Design Tokens Community Group (DTCG)](https://design-tokens.github.io/community-group/format/)
JSON format and live under `tokens/`:

| File | Scope |
| --- | --- |
| `colors.json` | Core palette (navy, gold, cream, accent, semantic, surface) |
| `colors.church.json` | Liturgical season colours (Advent, Lent, Easter, Ordinary, feast days) |
| `typography.json` | Font families, sizes, line heights, letter spacing, weights |
| `spacing.json` | Spacing scale (4 px base grid) |
| `breakpoints.json` | Responsive breakpoints (mobile, tablet, desktop, wide) |
| `elevation.json` | Shadow tokens for surface depth |
| `radius.json` | Border radius scale |
| `icons.json` | Icon sizing and grid |
| `motion.json` | Duration and easing tokens |

Tokens are validated by `tools/validate_tokens.py` for:
- DTCG JSON Schema conformance (draft 2020-12)
- `$type` correctness and alias resolution (with cycle detection)
- Cross-file drift between source tokens, generated CSS and Figma output

## Brand assets

| Directory | Contents |
| --- | --- |
| `assets/logo/master/` | SVG logo masters (horizontal, vertical, logomark) |
| `assets/logo/construction/` | Clearspace and construction diagrams |
| `assets/logo/inverse/` | Inverse colour variants (gold on navy, navy on gold) |
| `assets/logo/monochrome/` | Single-colour variants (black, white) |
| `assets/logo/raster-exports/` | README per format naming every derived file |
| `assets/favicon/` | SVG favicon source |
| `assets/imagery/motif/` | Ichthys geometry and pattern tile SVGs |
| `assets/imagery/liturgical/` | Licensed liturgical photography |
| `assets/typography/` | SIL OFL-licensed font families (Fraunces, Inter) |
| `assets/og/` | Open Graph card template |
| `assets/social/` | Social media banner |

## Build and validation tooling

All tooling lives under `tools/` and is installed from `tools/requirements.txt`:

| Script | Purpose |
| --- | --- |
| `validate_tokens.py` | DTCG schema, type checks, alias cycles, CSS/Figma drift |
| `build_exports.py` | Figma Variables, raster logos, favicons, OG cards, WOFF2 subsets |
| `contrast_check.py` | WCAG 2.x relative-luminance contrast verification |
| `cyrillic_check.py` | Font `cmap` coverage for LT/RU locale alphabets |

Build outputs (all generated, not committed except where noted):
- `build/css/tokens.css` — CSS custom properties (committed)
- `build/figma-tokens/tokens.json` — Figma Variables import (committed)
- `build/tailwind.preset.ts` — Tailwind CSS preset (committed)
- `build/ts/index.ts` — TypeScript token definitions (committed)
- `build/css/reset.css` — CSS reset aligned to token values (committed)
- `build/package.json` — npm distribution manifest

## Repository layout

```text
viavitae-brand/
+-- README.md                     # This file
+-- LICENSE                       # Proprietary - All Rights Reserved, EU/LT jurisdiction
+-- SECURITY.md                   # Disclosure policy, SLA table, safe harbour, scope
+-- QODER.md                      # Behavioural guidelines for AI-assisted coding
+-- CONTRIBUTING.md               # Contribution workflow, PR rules, DCO sign-off
+-- CHANGELOG.md                  # Keep a Changelog driven by Conventional Commits
+-- .gitignore                    # Node + Python + export artefacts
+-- .editorconfig                 # Deterministic formatting across editors
+-- .github/
|   +-- CODEOWNERS                # Owner mapping, R2 baseline
|   +-- dependabot.yml            # Weekly grouped updates
|   +-- PULL_REQUEST_TEMPLATE.md  # PR checklist including compliance items
|   +-- ISSUE_TEMPLATE/
|   |   +-- bug_report.yml        # Structured bug report form
|   |   +-- feature_request.yml   # Structured feature request form
|   +-- workflows/
|       +-- ci.yml                # Lint, typecheck, test, SAST, dependency scan, build
|       +-- compliance-check.yml  # Secrets, licences, governance file presence
|       +-- codeql.yml            # Static analysis
+-- tokens/                       # W3C DTCG design token source files
+-- assets/                       # SVG masters, typography, imagery
+-- build/                        # Generated distribution artefacts (committed by design)
+-- tools/                        # Python validation and export scripts
+-- examples/                     # Consumer integration examples
+-- guidelines/                   # Brand usage guidelines
+-- docs/
    +-- architecture.md           # MADR architecture decision records
    +-- DPIA-template.md          # GDPR Article 35 assessment template
```

## Development workflow

1. Branch from `main` using a conventional prefix: `feat/`, `fix/`, `chore/`, `docs/`.
2. Commit using Conventional Commits — the changelog is derived from these messages.
3. Self-review against `QODER.md` if you used AI assistance.
4. Open a pull request; the template pre-fills the compliance checklist.
5. Pass the gates: CI, compliance, CodeQL, and one architect review.
6. Squash and merge. Trunk-based: no long-lived feature branches.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and the DCO sign-off line.

## Quality gates

Every pull request must pass:

| Gate | Tool | Threshold |
| --- | --- | --- |
| Lint | `ruff` | zero findings |
| Format | `ruff format` | no diff |
| Types | `mypy --strict` | zero errors |
| Token validation | `validate_tokens.py` | zero defects |
| SVG master checks | `build_exports.py --check` | zero structural defects |
| Contrast | `contrast_check.py` | all pairs pass WCAG AA |
| SAST | Semgrep, CodeQL | zero findings at or above the failure severity |
| Dependencies | Trivy filesystem | fail on `CRITICAL` |
| Secrets | Gitleaks, full history | fail on any finding |
| Licences | allow-list scan | unknown licence fails and is labelled for review |
| Governance | presence checks | all required files present and non-empty |

## Security and compliance

- To report a vulnerability, follow the private disclosure process in
  [SECURITY.md](SECURITY.md). Do **not** open a public issue. Acknowledgement is within
  24 hours, triage within 72 hours.
- Personal-data processing requires a completed
  [DPIA](docs/DPIA-template.md) under GDPR Article 35 before processing starts (R5).
- Architectural choices with security, privacy or data-residency impact are recorded as an
  [ADR](docs/architecture.md).
- A GDPR personal-data breach is notified to the supervisory authority within 72 hours of
  awareness; see the breach workflow in [SECURITY.md](SECURITY.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [SECURITY.md](SECURITY.md) | Disclosure policy, SLA table, safe harbour, scope. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution workflow, PR rules, DCO sign-off. |
| [CHANGELOG.md](CHANGELOG.md) | Release history in Keep a Changelog format. |
| [QODER.md](QODER.md) | AI pair-programming guardrails and stop-conditions. |
| [docs/architecture.md](docs/architecture.md) | MADR decision records and index. |
| [docs/DPIA-template.md](docs/DPIA-template.md) | GDPR Article 35 assessment template. |

## Licence

Proprietary — All Rights Reserved. (c) ViaVitae IT Technologies. No redistribution, no
derivative works and no commercial use by third parties without a written agreement.
Governed by the law of Lithuania (EU). See [LICENSE](LICENSE).
