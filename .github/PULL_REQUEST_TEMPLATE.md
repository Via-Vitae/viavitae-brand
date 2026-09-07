# Pull Request

<!--
Pull request template for every repository generated from viavitae-template.

Complete every box. A box that genuinely does not apply is annotated "n/a" with a
reason — it is not left blank. Blank boxes are treated as "not done" and the review
is returned.

Before opening this pull request, read CONTRIBUTING.md for the small-PR doctrine
(under 400 changed lines) and QODER.md if you used AI assistance.
-->

## Summary

<!-- One or two sentences: what changes, and why. Link the design or ADR if there is one. -->

## Linked issue

<!-- Closes #123 — use the keyword so the issue closes automatically. Write "n/a" with a reason if there is no issue. -->

Closes #

## Type of change

<!-- Keep one, delete the rest. -->

- [ ] `feat` — a new feature
- [ ] `fix` — a bug fix
- [ ] `perf` — a performance improvement
- [ ] `refactor` — restructuring, no behaviour change
- [ ] `docs` — documentation only
- [ ] `test` — tests only, no production change
- [ ] `build` / `ci` — build system, dependencies or CI configuration
- [ ] `chore` — maintenance, touches neither source nor tests
- [ ] `revert` — reverting a previous commit
- [ ] **Breaking change** — append `!` to the commit type and describe the migration below

## Checklist

### Change quality

- [ ] **Conventional Commit title** — `<type>(<scope>): <imperative summary>`, under 72 characters, per CONTRIBUTING.md
- [ ] **Linked issue** — `Closes #nnn` above, or "n/a" with a reason
- [ ] **Tests added/updated** — new behaviour has a test; a fix has a regression test that fails without it
- [ ] **Linters and typecheck pass locally** — `ruff`, `ruff format --check`, `mypy --strict`, `eslint`, `tsc --noEmit`, `terraform fmt -check` as applicable
- [ ] **No secrets in diff** — Gitleaks run locally over the full history, no credential, token, key or connection string anywhere in the change
- [ ] **No new deps without justification** — every added dependency is named below with the reason, the licence, and why an existing dependency could not do the job

### Compliance

- [ ] **GDPR impact assessed** — if personal data is touched, a DPIA reference is given below; if not, this box is annotated "n/a — no personal data"
- [ ] **Accessibility checked (WCAG 2.2 AA)** — if UI is touched: keyboard path, visible focus, programmatic name, colour contrast, `axe` gate green; otherwise "n/a — no UI"
- [ ] **i18n parity LT/EN/RU** — if user-facing strings are touched, all three locales updated in this change; otherwise "n/a — no strings"

### Documentation

- [ ] **CHANGELOG entry** — follows from the commit type, or the change is `test`/`chore` and is not released
- [ ] **Docs updated** — README, ADR, runbook or API reference reflect the change, or no user-visible behaviour changed
- [ ] **Screenshots for UI changes** — before and after, at desktop and mobile width, or "n/a — no UI"

## New dependencies

<!-- One row per added dependency. Delete the table if none. -->

| Package | Version | Licence | Why an existing dependency could not do this |
| --- | --- | --- | --- |
| | | | |

## GDPR and DPIA

<!--
Required if this change touches personal data. Under rule R5, processing may not
start before the DPIA is complete.
-->

| Field | Value |
| --- | --- |
| Personal data affected | none / identify which |
| Special category data (Art. 9), including religious belief | no / yes — condition relied on |
| DPIA reference | n/a / DPIA-nnn |
| New processor or subprocessor | no / name, DPA in place, EEA residency confirmed |
| Data residency | EEA-only confirmed / exception requested — link the ADR |
| Retention period changed | no / old and new period |

## Breaking changes and migration

<!-- Required if "Breaking change" is selected above. Otherwise write "none". -->

## AI assistance

<!--
Required disclosure, per QODER.md. State which parts were AI-assisted and confirm
you have read and can defend every line.
-->

- [ ] No AI assistance was used
- [ ] AI assistance was used — I have reviewed every line, confirmed no invented files, no stubs and no placeholders, and I take responsibility for the result

## Verification

<!--
How did you prove this works? Paste the commands you ran and the relevant output.
"Tested locally" without evidence is not verification.
-->

## Size

- [ ] Under 400 changed lines, excluding generated files and lockfiles — or the reason is stated in the summary and review was requested early
