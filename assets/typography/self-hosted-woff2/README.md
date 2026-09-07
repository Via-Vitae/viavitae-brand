# Self-hosted WOFF2 bundle

This directory is where the brand's fonts are built for self-hosting, and it is
empty in a fresh clone. Nothing here is committed except this README.

`.gitignore` excludes `*.ttf`, `*.otf`, `*.woff` and `*.woff2` and the
`.*.instanced.ttf` intermediate, so a several-hundred-kilobyte binary cannot enter
git history by accident. Font binaries in history are retained by every clone
forever, whether or not anyone still needs them, and a variable font is large
enough that one careless commit is a permanent cost to every future checkout.

## What the licence allows

Both families are SIL Open Font License 1.1. OFL permits use, study, modification
and redistribution freely, and permits bundling and embedding with any software,
subject to conditions — chiefly that the font is not sold by itself, that each
redistributed copy carries the copyright notice and the licence text, and that a
modified version does not use the Reserved Font Name without written permission.

Subsetting produces a Modified Version in OFL terms, so the notice has to travel
with it. That notice is in this repository and is committed:

- [`../fraunces/OFL-licence.md`](../fraunces/OFL-licence.md)
- [`../inter/OFL-licence.md`](../inter/OFL-licence.md)

Ship those two files alongside the WOFF2 output. `.github/workflows/compliance-check.yml`
asserts both exist and both contain the OFL preamble, because the licence record
is the part of this directory that has to survive a clean build.

## Building the bundle

```bash
pip install -r tools/requirements.txt        # needs fonttools and brotli
```

Download the two variable fonts from their own release pages and place them in
this directory under exactly these names, which is what `FONT_SOURCES` in
`tools/build_exports.py` looks for:

```
assets/typography/self-hosted-woff2/Fraunces-Variable.ttf
assets/typography/self-hosted-woff2/Inter-Variable.ttf
```

Then:

```bash
python3 tools/build_exports.py --fonts
```

Nine files are produced:

```
fraunces-300.woff2   fraunces-400.woff2   fraunces-500.woff2
fraunces-600.woff2   fraunces-700.woff2
inter-400.woff2      inter-500.woff2      inter-600.woff2      inter-700.woff2
```

If a source TTF is absent the step reports a skip with the reason rather than
failing, because an empty clone is the normal state and a red build for it would
train contributors to ignore red builds.

## Why Fraunces ships a 300 and Inter does not

`tokens/typography.json` declares five permitted weights — 300, 400, 500, 600 and
700 — and the bundle does not carry all five for both families. That is deliberate
and it follows from where each face is set. A display face is set large, where a
light weight reads as refinement; a UI face is set at 14 to 16 pixels, where 300 is
too thin to hold its counters and too thin to pass a contrast-sensitive reading on
a low-quality panel. So `fontWeight.light` is available for `fontFamily.display`
and is not built for `fontFamily.ui`.

**The consequence is a silent failure, so it is worth stating exactly.** No
`typeScale` entry currently references `{fontWeight.light}` at all. If a design
starts using weight 300 with the UI stack, the browser finds no `@font-face`
declaring 300 and picks the nearest one it has, which is 400. Nothing warns,
nothing synthesises, the text simply renders at the wrong weight. Adding the
weight to `FONT_SOURCES` in the same commit as the design change is the fix, and
the payload cost of one more subset is the price.

## What the subset keeps

`SUBSET_RANGES` in `tools/build_exports.py` is the authoritative list. It covers
Basic Latin, Latin-1 Supplement, Latin Extended-A and B, spacing modifier
letters, combining diacriticals, the Cyrillic block, Cyrillic Ghe with upturn,
general punctuation, currency, arrows, mathematical operators, geometric shapes
and the alphabetic presentation forms.

Two entries in that list are there because the obvious configuration gets them
wrong:

- **U+0400–U+045F**, not U+0410–U+044F. The letter Io — Ё and ё, at U+0401 and
  U+0451 — sits outside the range a subsetter configured with "Cyrillic means
  U+0410 to U+044F" would keep, and Russian liturgical text uses it constantly. A
  subset that drops it renders every Ё as a box or as a fallback glyph, in the one
  part of the product where the text matters most. `tools/cyrillic_check.py`
  asserts both codepoints are present.
- **U+2000–U+206F**, general punctuation. The en dash, the em dash, the curly
  quotes and the ellipsis live here. `locale.en.requiredCodepoints` names them
  individually, and a subset that omits the block turns every piece of correct
  typography in the content into a missing-glyph box.

Layout features retained: `kern, liga, clig, ccmp, locl, mark, mkmk, rlig, tnum,
lnum`. `locl` is the one that matters for a trilingual product — it selects the
locale-appropriate glyph form — and `tnum` is what makes `tabular-nums` work.
`mark` and `mkmk` position the combining diacritics, without which the Lithuanian
ogoneks and carons are placed by the shaper's guesses.

## Two passes, not one

A variable font is first pinned to the requested `wght` with
`fontTools.varLib.instancer`, and the resulting static font is then subsetted with
`fontTools.subset`. There is no single command that does both: `pyftsubset` has no
instancer flag. Subsetting a variable font without pinning it keeps the whole
`gvar` table, which is most of the file size and none of the benefit, because a
browser that only ever requests weight 600 downloads every weight.

## Status of this build step

**The `--fonts` path has not been run against a real font binary.** fontTools is
not installed in the environment where it was written, the argument lists are
taken from the fontTools documentation, and `--check` does not cover it. Run it
once against the two TTFs, confirm the nine outputs, confirm the glyph counts with
`tools/cyrillic_check.py --font-dir assets/typography/self-hosted-woff2`, and
only then wire it into CI. Everything else in `tools/build_exports.py` — the SVG
checks, the Figma sync, the CSS drift comparison — is exercised and green.

## Serving the bundle

`tokens/typography.json` declares the strategy under `com.viavitae.loading`:
`self-hosted-woff2` as the strategy, `google-fonts` as the fallback, `swap` as
`font-display`, and preloading of weights 400 and 600. Metric overrides for the
fallback face are under `com.viavitae.fallback-metrics`, and they are what turns
the `swap` reflow into a colour and texture change rather than a layout change.

Self-hosting is the default for any deployment serving EU residents. A Google
Fonts stylesheet request sends the visitor's IP address and user agent to a
US-controlled third party at page load, before any consent decision. That is the
pattern German courts have ruled unlawful and the CNIL has flagged, and for a
product whose customers are parishes and dioceses it is not a risk to take for the
convenience of one `<link>` element.
