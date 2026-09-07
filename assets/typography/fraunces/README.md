# Fraunces — the display family

Fraunces is the brand's display face: headings, cover lines, pull quotes and
anything set large enough to be read as a design decision rather than as text.
It is not used for body copy, forms, navigation or tables — that is Inter.

| | |
| --- | --- |
| Role | `fontFamily.display` in `tokens/typography.json` |
| Licence | SIL Open Font License 1.1 — see [`OFL-licence.md`](./OFL-licence.md) |
| Format | Variable font, `wght` 100–900 |
| Weights the brand may request | 300, 400, 500, 600, 700 (`fontWeight.*`) |
| Google Fonts | <https://fonts.google.com/specimen/Fraunces> |
| Upstream | <https://github.com/undercasetype/Fraunces> |
| Rationale | `docs/architecture.md` — ADR-003 |
| Usage rules | `guidelines/typography-usage.md` |

## Cyrillic is the thing to know about this family

**Fraunces does not declare Cyrillic coverage.** `tokens/typography.json`
therefore declares a separate display stack for Russian:

```json
"display-cyrillic": ["Noto Serif", "PT Serif", "Georgia", "serif"]
```

and `locale.ru.fontFamilyDisplay` points at it. This is not a cosmetic fallback.
A Russian heading set in Fraunces does not render as "Fraunces with some missing
glyphs"; it renders **glyph by glyph**, with the Latin lookalikes in Fraunces and
the Cyrillic letters in whatever the browser's default serif happens to be. The
result is a heading in two typefaces, which is silent in an English-only review,
invisible in a screenshot of the English site, and obvious to every Russian
reader. `tools/cyrillic_check.py` exists to make that failure a build failure.

If Fraunces ever adds Cyrillic, the change is: point `locale.ru.fontFamilyDisplay`
at `{fontFamily.display}`, run `tools/cyrillic_check.py` against the new binaries
with the font files present, and record the decision in `CHANGELOG-ASSETS.md`.
Do not make the change on the strength of a release note.

## Lithuanian is covered

Lithuanian adds nine letters to the Latin alphabet — ą č ė ę į š ų ū ž — eighteen
codepoints across both cases, all in Latin Extended-A (U+0100–U+017F), which
Fraunces declares support for. `locale.lt.fontFamilyDisplay` therefore points at
`{fontFamily.display}` directly, with no substitution.

Two constraints follow from the shapes rather than from the coverage, and both are
in `locale.lt.notes`: the ogonek hangs below the baseline and the caron sits above
the cap line, so a display line-height below 1.15 clips Lithuanian body copy; and
`text-transform: uppercase` is safe for Lithuanian but a caron clipped by a tight
line box is not recoverable in CSS.

## Self-hosting

The default deployment strategy is `self-hosted-woff2`, not Google Fonts. A Google
Fonts stylesheet request sends the visitor's IP address and user agent to a
US-controlled third party at page load, before any consent decision, which is the
pattern German courts have ruled unlawful and which the CNIL has flagged. For a
product serving parishes and dioceses in the EU that is not a risk to accept for
the convenience of a `<link>`.

See [`../self-hosted-woff2/README.md`](../self-hosted-woff2/README.md) for the
build steps and [`OFL-licence.md`](./OFL-licence.md) in this directory for the
notice that has to travel with any redistributed file.

## Variable axes

Fraunces ships as a variable font with design axes beyond `wght`. The brand does
**not** use them, and `tokens/typography.json` deliberately declares no axis
settings for this family. Two reasons: an axis setting is a design decision that
has to be made once and applied everywhere, and an optical size axis interacts
with the type scale in a way that would have to be verified at every step of it.
If a future design wants a wonky display treatment, that is an ADR, a token, and
an assertion in `tools/cyrillic_check.py`'s style that the axis range actually
exists in the shipped binary — not a CSS property added to one component. Read the
axis list off the release archive before proposing one; do not read it off this
file, which deliberately does not claim to know it.

## OpenType features the brand does use

Declared in `tokens/typography.json` under `fontVariant`, and each one carries a
note that it must be confirmed against the shipped font file, because a CSS
request for a feature the font does not implement is silently ignored:

- `lining-nums` — set explicitly rather than relying on the font default, because
  Fraunces offers oldstyle figures as an alternate and the default varies with
  optical size.
- `proportional-nums` — for Fraunces display type and running prose, where
  oldstyle or proportional figures belong to the texture of the face.
- `tabular-nums` — required in any column of numbers. Fraunces is a display face
  and columns of figures are Inter's job, but the token exists so the rule is
  stated once.
- `common-ligatures` — on for prose, off for uppercase overlines and navigation,
  where the fi and fl joins read as errors at small sizes.
