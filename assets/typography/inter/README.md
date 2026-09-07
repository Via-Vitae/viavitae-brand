# Inter — the UI family

Inter is the brand's interface face: body copy, navigation, forms, tables,
buttons, labels, captions and every column of figures. It is the type a reader
spends most of their time in, which is exactly why it is not the interesting one.
Headings are Fraunces.

| | |
| --- | --- |
| Role | `fontFamily.ui` in `tokens/typography.json` |
| Licence | SIL Open Font License 1.1 — see [`OFL-licence.md`](./OFL-licence.md) |
| Format | Variable font, `wght` 100–900 |
| Weights the brand may request | 300, 400, 500, 600, 700 (`fontWeight.*`) |
| Google Fonts | <https://fonts.google.com/specimen/Inter> |
| Upstream | <https://rsms.me/inter/> and <https://github.com/rsms/inter> |
| Rationale | `docs/architecture.md` — ADR-003 |
| Usage rules | `guidelines/typography-usage.md` |

## Inter covers Cyrillic, and that is why the UI stack does not change

`locale.ru.fontFamilyUi` is `{fontFamily.ui}` — the same stack as Lithuanian and
English. Inter declares the Cyrillic and Cyrillic Extended blocks, so a Russian
interface is set in the same face as a Lithuanian one and the brand looks like
itself in all three languages.

This is the difference between the two families and it is worth stating plainly,
because the asymmetry is easy to get wrong when adding a locale: **the display
stack changes for Russian and the UI stack does not.** One family covers
Cyrillic, the other does not, and a single `font-family` declaration cannot
absorb that. `tools/cyrillic_check.py` verifies the declared requirement against
the actual binaries for every locale marked `supported`, and treats a locale with
no reference alphabet as a hard failure rather than passing it silently.

## Lithuanian is covered

All eighteen codepoints Lithuanian adds — the nine letters ą č ė ę į š ų ū ž in
both cases — are in Latin Extended-A, which Inter declares. Inter is also the
family where the diacritics matter most in practice, because it is set small: an
ogonek at 14px in a form label is a shape the reader has to recognise, not a
detail. `locale.lt.notes` carries the constraint that follows: no display
line-height below 1.15 on Lithuanian body copy, and never an overline whose
uppercase transform would clip a caron.

## Tabular figures are a requirement, not a preference

`fontVariant.numerals-tabular` (`tabular-nums`) is REQUIRED in any column of
numbers: a table of donation amounts, a date list, a metric card, a countdown.
Without it the digits are proportionally spaced and columns jitter as values
change, which makes a total unreadable and a live-updating figure visibly twitch.
Inter is one of the families where the difference is easy to miss in a static
mockup and impossible to miss in a running one.

Set `font-variant-numeric: tabular-nums` on the container of the column rather
than on each cell, so the alignment cannot be broken by a cell that forgets it.

## Self-hosting

Same policy as Fraunces and for the same reason: the default deployment strategy
is `self-hosted-woff2`. A Google Fonts request sends the visitor's IP address and
user agent to a US-controlled third party at page load, before consent, which for
a product serving EU parishes and dioceses is not a trade worth making for one
`<link>` element.

Inter is the heavier of the two to self-host, because it is loaded on every page
at two weights (`com.viavitae.loading.preloadWeights` is `[400, 600]`) while
Fraunces is loaded only where a display face appears. That makes subsetting worth
the build step. See [`../self-hosted-woff2/README.md`](../self-hosted-woff2/README.md).

## Loading

`font-display: swap`, with metric overrides on the fallback face declared under
`com.viavitae.fallback-metrics` in `tokens/typography.json`. `swap` was chosen
over `block` and `optional` and the reasoning is recorded in the token file:
`block` hides all text for up to three seconds on a slow connection, which on a
funeral page means a bereaved family stares at a blank screen; `optional` avoids
layout shift but routinely serves the fallback for the whole session on a slow
network, so the brand face is seen by exactly the users with the worst connection.
`swap` shows the fallback immediately and upgrades, and the cost — one reflow — is
bounded by the fallback's `size-adjust` and `ascent-override`.
