# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries are derived from [Conventional Commits](https://www.conventionalcommits.org/). A
commit whose title does not parse produces no release note, which is a defect in the
commit, not in the changelog.

## Commit types

| Type | Changelog section | Meaning |
| --- | --- | --- |
| `feat` | **Added** | A new feature. |
| `fix` | **Fixed** | A bug fix. |
| `perf` | **Changed** | A code change that improves performance. |
| `refactor` | **Changed** | A code change that neither fixes a bug nor adds a feature. |
| `docs` | **Documentation** | Documentation-only changes. |
| `test` | not released | Adding or correcting tests. |
| `build` / `ci` | **Infrastructure** | Build system, dependencies, or CI changes. |
| `chore` | not released | Other changes that do not modify source or tests. |
| `revert` | **Reverted** | Reverting a previous commit. |

Append `!` after the type or scope, and add a `BREAKING CHANGE:` footer, to mark a
**breaking change**. Breaking changes trigger a major version bump and are called out at
the top of the release section with the migration steps.

## Enforcement

Changelog accuracy is enforced mechanically, not by goodwill:

- **Commits** are validated against the Conventional Commits grammar in CI. A malformed
  title fails the lint job.
- **Releases** are produced by `release-please` from the conventional commit history. It
  opens a release pull request that updates this file and bumps the version; merging it
  creates the tag. Where `release-please` is not enabled on a repository, the manual rule
  applies instead: the release pull request must update this file in the same change that
  bumps the version, and a version header without a date is a review blocker.
- **Every section** below a version header is present, even when empty, marked _None._ This
  makes a missing section visible as an omission rather than invisible as an absence.
- **Security** entries for a vulnerability are published only after the fix is deployed,
  and link the advisory rather than describing the exploit. See
  [SECURITY.md](SECURITY.md).

## Version headers

Format: `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD`, using the UTC release date. The `Unreleased`
section collects changes that have landed on `main` but are not yet tagged.

Compare links for each version are maintained at the bottom of this file.

---

## [Unreleased]

### Added

_None._

### Changed

_None._

### Deprecated

_None._

### Removed

_None._

### Fixed

_None._

### Security

_None._

### Documentation

_None._

### Infrastructure

_None._

### Reverted

_None._

---

## [1.0.0] - 2026-09-06

Initial release of the ViaVitae repository template. Every repository in the
`Via-Vitae` organisation is generated from this baseline.

### Added

- Governance baseline: `README.md` with the generate-from-template procedure, governance
  rules R1 to R5, and the repo-type adaptation checklist for web, api, infra, docs and qa.
- `LICENSE` — proprietary, All Rights Reserved, (c) ViaVitae IT Technologies, governed by
  the law of Lithuania (EU) with exclusive jurisdiction in Vilnius.
- `SECURITY.md` — private disclosure to `security@viavitae.com`, acknowledgement within 24
  hours, triage within 72 hours, remediation SLA table, GDPR Article 33 72-hour breach
  notification workflow, safe harbour for good-faith researchers, and scope covering all
  `Via-Vitae` repositories, demo subdomains and `jolarca.com`.
- `QODER.md` — seven behavioural rules for AI-assisted coding, including compliance
  stop-conditions for GDPR, WCAG 2.2 AA, EU data residency and secrets.
- `CONTRIBUTING.md` — trunk-based development, branch naming, Conventional Commits, DCO
  sign-off, pull request rules, the under-400-line small-PR doctrine, and local quality
  gates.
- `CHANGELOG.md` — Keep a Changelog format driven by Conventional Commits, with the
  enforcement note for `release-please` and the manual fallback rule.
- `.gitignore` — Node, Python and Terraform superset, excluding state files, environment
  files, keys and secrets directories.
- `.editorconfig` — UTF-8, LF, final newline, trimmed trailing whitespace, 2-space indent
  for web and data formats, 4-space for Python, tab for `Makefile`, 100-column limit
  except Markdown.
- `.github/CODEOWNERS` — `*` to `@Via-Vitae/architects`, with per-path rules for
  platform, compliance, security, legal and DPO ownership, and the R2 immutability rule.
- `.github/dependabot.yml` — weekly grouped updates on Monday 06:00 Europe/Vilnius across
  npm, pip, github-actions, terraform and docker, limit 10 open pull requests, reviewed by
  architects, `chore(deps)` commit prefix, and ignore rules for pinned majors.
- `.github/PULL_REQUEST_TEMPLATE.md` — checklist covering Conventional Commit title, linked
  issue, tests, local gates, secrets, dependency justification, GDPR and DPIA, WCAG 2.2 AA,
  i18n parity for LT/EN/RU, changelog entry, docs and UI screenshots.
- `.github/ISSUE_TEMPLATE/bug_report.yml` — structured form with severity, affected
  repository and version, environment, reproduction steps, expected versus actual, PII-scrub
  instructions for logs, GDPR-relevance flag and a sensitive-data warning block.
- `.github/ISSUE_TEMPLATE/feature_request.yml` — structured form with problem statement,
  proposed solution, alternatives, compliance impact, EU-only check, i18n impact, estimated
  scope and acceptance criteria.
- `.github/workflows/ci.yml` — setup, lint, typecheck, unit tests with an 80% coverage gate,
  Semgrep SAST, Trivy filesystem dependency scan failing on CRITICAL, and build artefact
  upload, on push to `main` and on all pull requests.
- `.github/workflows/compliance-check.yml` — Gitleaks over full history failing on any
  finding, licence allow-list scan with unknown licences failing and labelled for manual
  review, and presence checks for `CODEOWNERS`, `.editorconfig` and `.gitignore`.
- `.github/workflows/codeql.yml` — CodeQL over a `python` and `javascript-typescript`
  matrix with the `security-and-quality` suite, weekly plus on push and on pull request,
  uploading results to code scanning.
- `docs/architecture.md` — MADR-format decision record template with status, context,
  decision, consequences, alternatives considered, compliance impact, owner and date, plus
  the `ADR-NNN` numbering convention and an index table.
- `docs/DPIA-template.md` — nine-section GDPR Article 35 assessment template with worked
  examples DPIA-001 (assessment funnel) and DPIA-002 (AI pastoral assistant).

### Changed

_None._

### Deprecated

_None._

### Removed

- `main.py` — the IDE-generated sample entrypoint. It was not part of the template tree and
  its presence caused Python linting, type checking and CodeQL analysis to run against
  non-Python repositories generated from this template.

### Fixed

_None._

### Security

_None._

### Documentation

_None._

### Infrastructure

_None._

### Reverted

_None._

---

[Unreleased]: https://github.com/Via-Vitae/viavitae-template/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Via-Vitae/viavitae-template/releases/tag/v1.0.0
