# Contributing

Thank you for contributing to a ViaVitae repository. This document describes the workflow
that applies to every repository generated from `viavitae-template`.

Read [QODER.md](QODER.md) before contributing with AI assistance, and
[SECURITY.md](SECURITY.md) before reporting anything security-related. Security reports
never go through a public issue or pull request.

---

## Code of conduct

Contributors, reviewers and maintainers are expected to treat each other with respect, to
critique work rather than people, and to assume good faith. Harassment, discrimination and
personal attacks are not accepted in any ViaVitae space, including issues, pull requests,
commit messages and chat.

Report a concern to `legal@viavitae.com`. Reports are handled confidentially. Where a
repository needs a full standalone code of conduct, one is added as `CODE_OF_CONDUCT.md`
and owned by `.github/CODEOWNERS`; this section remains the binding baseline until then.

Because ViaVitae serves religious communities, contributors additionally commit to
respecting the confidentiality and dignity of data subjects — many of whom are members of a
congregation and never consented to their data being discussed in a public forum.

## Development model: trunk-based

We work trunk-based. `main` is always deployable, always protected, and always moving.

- Branch from `main`, merge back to `main`. No long-lived feature branches.
- A change that is not ready to ship goes behind a feature flag, not onto a branch that
  lives for a month.
- Releases are cut from `main` as tags. Release branches, where they exist, receive fixes
  only.
- Force-pushes to `main` are disabled. Review dismissal is disabled. Administrators are
  not exempt from branch protection.

## Branch naming

Prefix every branch with its type. The prefix drives changelog grouping and reviewer
routing.

| Prefix | Use | Example |
| --- | --- | --- |
| `feat/` | A new feature | `feat/assessment-funnel-quote` |
| `fix/` | A bug fix | `fix/donation-webhook-idempotency` |
| `chore/` | Maintenance, dependencies, tooling | `chore/pin-action-shas` |
| `docs/` | Documentation only | `docs/dpia-002-approval-queue` |
| `test/` | Tests only, no production change | `test/k6-assessment-thresholds` |
| `ci/` | CI configuration only | `ci/trivy-fail-on-critical` |
| `refactor/` | Restructuring, no behaviour change | `refactor/tenant-model-split` |

Keep names lowercase, hyphen-separated, and under 50 characters. Include the issue number
where one exists: `fix/214-webhook-idempotency`.

## Conventional Commits

Every commit message follows [Conventional Commits](https://www.conventionalcommits.org/).
The changelog is generated from these messages, so a malformed title means a missing
release note.

```text
<type>(<scope>): <imperative summary, max 72 characters>

<optional body: what changed and why, wrapped at 100 columns>

<optional footer: BREAKING CHANGE, Closes #123>

Signed-off-by: Your Name <you@viavitae.com>
```

| Type | Meaning | Changelog section |
| --- | --- | --- |
| `feat` | A new feature | **Added** |
| `fix` | A bug fix | **Fixed** |
| `perf` | A performance improvement | **Changed** |
| `refactor` | Restructuring, no behaviour change | **Changed** |
| `docs` | Documentation only | **Documentation** |
| `test` | Adding or correcting tests | not released |
| `build` | Build system or dependencies | **Infrastructure** |
| `ci` | CI configuration | **Infrastructure** |
| `chore` | Other changes that touch neither source nor tests | not released |
| `revert` | Reverting a previous commit | **Reverted** |

Rules:

- Use the imperative mood: "add coverage gate", not "added coverage gate".
- Scope is the module or area affected, in parentheses: `feat(api):`, `fix(web):`.
- Append `!` for a breaking change, and repeat it in a `BREAKING CHANGE:` footer
  describing the migration: `feat(api)!: change tenant id to uuid`.
- Reference the issue in the footer, not the title: `Closes #123`.
- Never mention a credential, token, customer name or personal data in a commit message.
  Commit messages are permanent and are scanned.

Configure sign-off and message checking locally:

```bash
git config --local user.name "Your Name"
git config --local user.email "you@viavitae.com"
git config --local format.signOff true
```

## Developer Certificate of Origin

Every commit carries a DCO sign-off line. The sign-off is a statement that you have the
right to submit the change, under the [Developer Certificate of Origin 1.1](https://developercertificate.org/):

```text
Signed-off-by: Your Name <you@viavitae.com>
```

Add it with `git commit -s`. A commit without a sign-off is rejected. The sign-off uses
your real name and your ViaVitae email address; anonymous or pseudonymous contributions
cannot be accepted, because we must be able to establish provenance for a proprietary
codebase.

Signing off certifies that you wrote the change or have the right to submit it under the
project licence, that you understand the change is contributed under
[LICENSE](LICENSE), and that any AI-assisted portion was reviewed by you and is your
responsibility.

## Pull request rules

A pull request may be merged only when **all** of the following hold:

1. **One approving review from an architect.** `CODEOWNERS` requests the reviewers; the
   architect approval is mandatory and cannot be self-granted. Path-specific owners —
   security, compliance, legal, DPO — must additionally approve changes to their paths.
2. **Green CI.** Every job in `.github/workflows/ci.yml` passes: lint, format, typecheck,
   unit tests at or above the coverage gate, SAST, dependency scan, build.
3. **Green compliance.** `.github/workflows/compliance-check.yml` passes: no secret found
   in the full history, every inbound licence allow-listed, governance files present.
4. **Clean CodeQL.** No new finding at or above the configured failure severity in
   `.github/workflows/codeql.yml`.
5. **A linked issue,** where one exists. Use `Closes #123` in the description so the issue
   closes automatically.
6. **The checklist in `.github/PULL_REQUEST_TEMPLATE.md` completed.** Unchecked boxes that
   genuinely do not apply are annotated "n/a" with a reason, not left blank.
7. **Linear history.** Rebase onto `main` rather than merging `main` into your branch.
   Merge method is squash.

## Small-PR doctrine: under 400 lines

Keep every pull request under **400 changed lines**, excluding generated files and
lockfiles. This is a hard house rule, not a preference.

Review defect-detection rate falls sharply once a change exceeds roughly 400 lines, and
reviewers begin approving rather than reading. A large change also increases the blast
radius of a revert and makes bisecting useless.

To keep changes small:

- Separate a refactor from the behaviour change it enables. Two pull requests, in order.
- Split a feature behind a flag and land it in slices.
- Move dependency upgrades into their own `chore(deps)` pull request, where Dependabot
  already does this for you.
- Put generated code, schema migrations and lockfile churn in a dedicated commit so a
  reviewer can skip it deliberately.

If a change genuinely cannot be reduced, say why in the description and request review
early, before it is finished, so the reviewer is not surprised.

## Local quality gates before pushing

Run these locally. CI is a safety net, not a substitute for checking your own work.

```bash
# Python
source .venv/bin/activate
ruff check .                      # lint
ruff format --check .             # format
mypy --strict .                   # types
pytest --cov --cov-fail-under=80  # tests, coverage gate

# Node / TypeScript
npm ci
npm run lint                      # eslint
npm run typecheck                 # tsc --noEmit
npm test                          # vitest or jest

# Infrastructure
terraform fmt -check -recursive
terraform validate
tflint --recursive
checkov -d .

# Governance, all stacks
git diff --check                  # whitespace errors
gitleaks detect --source . -v     # secrets, full history
```

Then confirm the diff is what you intended and nothing more:

```bash
git status
git diff --stat
git diff main...HEAD
```

## AI-assisted contributions

AI assistance is welcome and is expected to follow [QODER.md](QODER.md). You are
accountable for everything in your pull request, including AI-generated portions.

Before opening a pull request that used AI assistance, confirm:

- no file was invented beyond the requested scope;
- no stub, placeholder, `TODO` or invented identifier reached the diff;
- the change was not a structural or architectural one that QODER rule 3 says to ask about
  first;
- existing codebase conventions were followed rather than the model's defaults;
- the diff is minimal, with no drive-by reformatting or refactoring;
- no GDPR, WCAG 2.2 AA, EU data residency or secrets stop-condition was worked around;
- you have read and understood every line, and can defend it in review.

Note in the pull request description that AI assistance was used and which parts. This is
not a penalty; it changes how a reviewer reads the diff.

## Compliance items that apply to every change

| Area | Requirement |
| --- | --- |
| **Personal data** | No new processing without a completed DPIA. See `docs/DPIA-template.md` and rule R5. |
| **Data residency** | Storage, backups, processors and CI runners stay in the EEA. |
| **Accessibility** | UI changes meet WCAG 2.2 AA and pass the `axe` gate. |
| **Internationalisation** | User-facing strings are added to `lt`, `en` and `ru` in the same change. |
| **Secrets** | Never committed, never logged, never in a fixture. Rotated immediately if exposed. |
| **Licences** | Inbound components carry an allow-listed licence. Copyleft requires legal review. |
| **Architecture** | A decision with security, privacy, residency or cost impact gets an ADR. |
| **Changelog** | The entry follows from the Conventional Commit type. |

## Getting help

| Question | Where |
| --- | --- |
| Workflow, review, branch or commit rules | This document, then `#engineering` |
| Architecture or design decisions | The architects, and record the outcome as an ADR |
| Personal data, DPIA, retention, processors | `dpo@viavitae.com` |
| Licensing and third-party components | `legal@viavitae.com` |
| Vulnerabilities and security incidents | `security@viavitae.com` — private, per [SECURITY.md](SECURITY.md) |

## Recognition

Contributors are recorded in the release notes generated from their Conventional Commits,
and in the ADRs they own. Sustained contribution to governance — templates, compliance
tooling, accessibility and privacy controls — is tracked by the architects and recognised
in review of CODEOWNERS path ownership.
