# Open Graph card

One file here is committed and one is generated.

| File | Status | Size | Source |
| --- | --- | --- | --- |
| `og-template-1200x630.svg` | committed | 1200 × 630 | itself — it is a master |
| `og-default.png` | generated | 1200 × 630 | the template, guides stripped |

Generate the card with:

```bash
pip install -r tools/requirements.txt   # needs Cairo: apt-get install libcairo2
python3 tools/build_exports.py --og
```

## The template draws guides the card does not have

`og-template-1200x630.svg` carries its safe zones as visible artwork, because a
template whose margins a designer cannot see is not a template — it is a file with
a number in its name. That guide layer sits between two sentinel comments:

```
<!-- GUIDES:BEGIN -->
<g id="guides"> ... </g>
<!-- GUIDES:END -->
```

`tools/build_exports.py` removes everything between those markers before it
rasterises, so `og-default.png` is the card and nothing else. The check step then
asserts both markers are still present, that stripping actually removed
something, that the result still parses as XML, and that no element with
`id="guides"` survived. Do not delete the markers and do not move card artwork
inside them.

The two safe zones are 80 units in from every edge, which is what survives the
crops and corner radii the platforms apply, and 120 units in, which is where the
type sits. Every piece of card content is inside the inner zone. The one element
deliberately outside it is the decorative vesica bleeding off the bottom-right
corner at 1.16:1 against the field: decoration may be cropped, content may not,
and that distinction is the whole of the rule.

## Making a card for a specific page

Copy the template, replace the three placeholder strings — the two title lines
and the standfirst — and change nothing else. The lockup, the accent rule, the
domain and the decorative mark are the constant part of the card, and they are
what makes a ViaVitae thumbnail recognisable in a feed before anybody reads it.
A card whose type moves is a card that no longer looks like the others.

Keep the title to two lines of sixty characters or fewer. Every platform
truncates at a width of its own choosing, and an ellipsis landing in the middle
of a name is worse than a shorter title.

## Wiring it up

```html
<meta property="og:image" content="https://viavitae.com/og-default.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="ViaVitae — Software for parishes, dioceses and the families they serve">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://viavitae.com/og-default.png">
```

`og:image` must be an absolute URL. A relative one is resolved against nothing in
most crawlers, and the failure is silent: the link previews with no image and no
error is raised anywhere the brand can see.

`og:image:alt` is not optional decoration. WCAG 2.2 SC 1.1.1 applies to the
preview a crawler builds as much as to the page it came from, and a screen reader
user scrolling a chat log encounters the card, not the article. Describe what the
card shows; do not repeat the title, which the platform already renders beside
it.

## Why 1200 × 630 and not something sharper

It is 1.91:1, the ratio Facebook, LinkedIn, X, Slack, Teams and WhatsApp all
display without letterboxing or cropping. A larger file is scaled down by every
one of them, so the extra bytes buy nothing; a different ratio is cropped by
somebody else's rules, which the brand neither controls nor can test. 1200 × 630
is the one size that arrives as drawn.
