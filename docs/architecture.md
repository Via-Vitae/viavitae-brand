# Architecture Decision Records

This file is the ADR index and template for the `viavitae-brand` repository. Every
architectural decision with a security, privacy, data-residency, cost or maintainability
consequence is recorded here. Decisions are made in conversations and lost; ADRs are how
a team remembers why the system is shaped the way it is, which is what makes it safe to
change later.

Records follow [MADR](https://adr.github.io/madr/) adapted for a regulated EU context: the
**Compliance impact** section is mandatory here, because under rules R1 and R5 a decision
that touches personal data or residency cannot be taken without it.

---

## When an ADR is required

Write an ADR before implementing, not after. An ADR written afterwards is a justification;
an ADR written before is a decision.

| Situation | ADR required |
| --- | --- |
| Introducing or replacing a build tool, token format or export pipeline | Yes |
| Adding a third-party dependency or font licence | Yes |
| Changing the token schema, alias resolution or type system | Yes |
| Changing which derived artefacts are committed vs generated | Yes |
| Diverging from `viavitae-template` governance or CI defaults (rule R1) | Yes |
| Accepting a dependency with a licence outside the allow list | Yes |
| Accepting a known security or accessibility finding as tolerable | Yes |
| A bug fix inside an existing agreed design | No |
| Adding a test, a translation, or documentation | No |

## Numbering convention

- Format: `ADR-NNN`, zero-padded to three digits, starting at `ADR-001`.
- Numbers are allocated sequentially from the index below and are **never reused**, even
  when a record is superseded or withdrawn. A retired number stays in the index so links
  from old pull requests and issues continue to resolve.
- The file heading is `## ADR-NNN: <short title in sentence case>`.
- Superseding a record does not delete it. Set its status to `Superseded by ADR-MMM` and
  leave the body intact. The history of what was tried and rejected is as valuable as the
  current decision.
- The ADR number is referenced in the commit message footer, the pull request description
  and any DPIA that depends on it.

## Status values

| Status | Meaning |
| --- | --- |
| `Proposed` | Under discussion. Implementation must not start. |
| `Accepted` | Agreed and in force. Implementation may proceed. |
| `Deprecated` | No longer applies to new work; existing systems may still depend on it. |
| `Superseded by ADR-MMM` | Replaced. Kept for history, links updated to the successor. |
| `Rejected` | Considered and declined. Kept so the question is not re-litigated. |

---

## Index

| ADR | Title | Status | Owner | Date |
| --- | --- | --- | --- | --- |
| [ADR-001](#adr-001-adopt-w3c-dtcg-token-format-and-source-first-build-model) | Adopt W3C DTCG token format and source-first build model | Accepted | Architects | 2026-09-08 |
| _ADR-002_ | _next available number_ | — | — | — |

New records are added at the end of this file and referenced from the table above, in the
same pull request. An ADR that is not in the index has not been made.

---

## ADR-001: Adopt W3C DTCG token format and source-first build model

| Field | Value |
| --- | --- |
| **Status** | Accepted |
| **Owner** | `@viavitae-org/architects` |
| **Date** | 2026-09-08 |
| **Deciders** | Architects, Security, Compliance |
| **Consulted** | Platform, Legal |
| **Supersedes** | — |
| **Superseded by** | — |

### Context

ViaVitae's brand system — design tokens, logo masters, typography and liturgical imagery
— needs a single repository that serves as the source of truth for every consumer: the
Next.js marketing site, the FastAPI backend, demo templates and the Figma design file.

The requirements are:

1. Tokens must be interoperable across design tools (Figma) and implementation stacks
   (CSS, TypeScript, Tailwind).
2. Derived artefacts (CSS custom properties, Figma Variables JSON, raster logos) must be
   reproducible from source, not hand-maintained.
3. SVG logo masters must be validated for structural correctness at commit time, because
   a corrupted master silently propagates to every derived format.
4. Font licensing (SIL OFL) requires that binary font files are not committed, while
   their licence texts and OFL notices are.
5. Liturgical imagery is committed (licensed brand asset) but must stay under 2 MB per
   file; full-resolution archives belong in object storage.

### Decision

The brand system repository adopts the W3C Design Tokens Community Group (DTCG) JSON
format as the token schema, with a source-first build model enforced by Python tooling:

1. **Token format**: W3C DTCG JSON in `tokens/*.json`. Each file covers one concern
   (colours, typography, spacing, breakpoints, elevation, radius, icons, motion). The
   liturgical colour set lives in a separate `colors.church.json` because it follows the
   liturgical calendar, not the core palette release cycle.

2. **Source-first build**: `tools/build_exports.py` generates every derived artefact from
   committed sources. The CI pipeline runs `build_exports.py --check` to assert that
   committed derived artefacts (CSS, Figma JSON, Tailwind preset, TypeScript definitions)
   match their sources by value.

3. **SVG master validation**: Every SVG under `assets/logo/` is validated for forbidden
   elements (clipPath, mask, filter, foreignObject, script, image, metadata), editor
   namespaces, viewBox correctness and title presence at commit time.

4. **Committed derived artefacts**: `build/css/tokens.css`, `build/figma-tokens/tokens.json`,
   `build/tailwind.preset.ts`, `build/ts/index.ts`, `build/css/reset.css` and
   `build/package.json` are deliberately committed so consumers can import them directly
   without running a build step. This is a documented departure from the template's
   `build/` ignore rule.

5. **Font binaries are not committed**: SIL OFL fonts are fetched from upstream release
   pages. Only OFL licence texts and README files are committed. WOFF2 subsetting is
   performed by the build pipeline when font binaries are present locally.

### Consequences

**Positive**

- Tokens are interoperable: Figma, CSS, TypeScript and Tailwind all derive from one
  source, so a colour change propagates everywhere in one commit.
- SVG corruption is caught at commit time, not when a consumer measures a wrong viewBox.
- The build is reproducible: the same sources produce the same artefacts regardless of
  who runs the build or when.
- Consumers (web, api, demos) import committed artefacts directly — no build step needed
  on their side for token consumption.

**Negative and accepted**

- Committed derived artefacts can drift from sources if the `--check` gate is bypassed.
  Accepted, because the gate runs in CI on every push and the alternative (no committed
  artefacts) forces every consumer to run the Python build.
- The W3C DTCG format is a moving standard. Accepted, because the validator pins the
  schema version and the token set is small enough to migrate if the standard changes.
- Font binaries must be fetched manually for local WOFF2 subsetting. Accepted, because
  committing several-hundred-kilobyte binaries for an OFL font contradicts the
  source-first principle and bloats every clone.

### Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Style Dictionary for token transforms | Adds a Node.js dependency to a Python-first tooling chain. The token set is small enough that a purpose-built Python pipeline is simpler to audit and has no transitive dependency surface. |
| Commit font binaries for convenience | Violates the OFL redistribution principle (the font is freely available upstream) and adds hundreds of kilobytes to every clone. The build pipeline handles subsetting when binaries are present. |
| Do not commit any derived artefacts | Forces every consumer to install Python tooling and run the build just to read a CSS custom property. The committed artefacts are validated for drift, so they cannot silently disagree with sources. |
| Use a proprietary token format (Figma-only) | Locks the brand system to one tool. The W3C DTCG format is tool-agnostic and the JSON schema is publicly auditable. |

### Compliance impact

| Area | Impact |
| --- | --- |
| GDPR | None. Design tokens and brand assets contain no personal data. |
| Article 9 special categories | None. Liturgical colours are abstract values, not personal data. |
| Data residency | None. No data is processed or stored by the brand system. |
| Breach notification, Art. 33 | None. |
| Accessibility, WCAG 2.2 AA | Positive. The contrast check gate (`contrast_check.py`) enforces WCAG AA contrast ratios for every declared colour pair at commit time, so a token change that breaks contrast cannot reach `main`. |
| Licensing | Positive. OFL font binaries are not committed (respecting redistribution terms); OFL licence texts are committed (compliance record). Liturgical imagery has a per-file licence record in `assets/imagery/liturgical/README.md`. The allow-list scan in `compliance-check.yml` enforces licence policy mechanically. |
| Supply chain | Positive. Python tooling dependencies are exactly pinned in `tools/requirements.txt`; GitHub Actions are SHA-pinned; no vendored dependencies. |
| New processors introduced | None. |
| Personal data processed | None. |

---

## ADR template

Copy everything below the line into a new section at the end of this file, assign the next
number from the index, and add the index row in the same pull request.

```markdown
## ADR-NNN: <short title in sentence case>

| Field | Value |
| --- | --- |
| **Status** | Proposed |
| **Owner** | <team handle, for example @viavitae-org/architects> |
| **Date** | <YYYY-MM-DD> |
| **Deciders** | <roles and teams that agreed> |
| **Consulted** | <roles and teams whose input was sought> |
| **Supersedes** | <ADR-NNN or —> |
| **Superseded by** | <ADR-NNN or —> |

### Context

<The situation and the force acting on it. What is true today, what constraint applies,
and why a decision is needed now. State the problem, not the preferred answer. Name the
regulatory, operational and technical constraints explicitly — GDPR, WCAG 2.2 AA, EEA data
residency, self-hosted Proxmox, existing contracts. Include the cost of doing nothing.>

### Decision

<The decision, in the active voice, specific enough to be implemented without further
interpretation. Number the constituent parts where there is more than one. A reader should
be able to tell whether an implementation conforms to this decision.>

### Consequences

<What becomes easier, what becomes harder, and what risk is knowingly accepted. Include the
negative consequences — an ADR that lists only benefits has not been thought through. State
migration cost, operational burden and what has to be undone if the decision is reversed.>

### Alternatives considered

<Each rejected alternative and the reason for rejection, as a table. Recording why an option
was declined prevents the same debate recurring when the person who declined it has left.>

### Compliance impact

<Effects on GDPR, lawful basis, special category data, data residency and transfers,
retention, breach exposure, accessibility and licensing. Whether a DPIA is required, and its
reference if one exists. Whether a new processor is introduced and whether a DPA is in place.
State "none" explicitly where there is genuinely no impact — a blank section is ambiguous.>
```
