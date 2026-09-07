# Social avatar and banner

One file here is committed and one is generated.

| File | Status | Size | Source |
| --- | --- | --- | --- |
| `banner-1500x500.svg` | committed | 1500 × 500 | itself — it is a master |
| `avatar-400.png` | generated | 400 × 400 | `assets/favicon/favicon.svg` |

Generate the avatar with:

```bash
pip install -r tools/requirements.txt   # needs Cairo: apt-get install libcairo2
python3 tools/build_exports.py --social
```

## The avatar comes from the filled favicon master

Not from the 512-unit logomark, and the reason is the same as for the icon set:
the logomark is monoline and its stroke becomes one grey pixel at small sizes.
`assets/favicon/favicon.svg` is the same vesica piscis geometry at one tenth
scale, drawn filled, on an opaque navy-900 plate.

The plate matters more for an avatar than for anything else the brand ships. A
platform crops an avatar to a circle of a size it chooses, over a background of a
colour it chooses, and a transparent mark survives neither decision. The artwork
sits inside the circle inscribed in the plate — its furthest corner is 24.2 units
from the centre of a 32-unit radius — so the crop removes the plate's corners and
none of the mark.

400 pixels is the largest common denominator: X asks for 400 × 400, LinkedIn for
400 × 400, Mastodon for at least 400 × 400, and every one of them downscales
rather than upscales when given more. A 400px source therefore arrives crisp on
all of them from one file.

## The banner is the deliverable, so it carries no guides

`banner-1500x500.svg` is uploaded to a platform as it is. There is no export step
that could strip anything, so every mark in that file ships. Unlike
`assets/og/og-template-1200x630.svg`, which draws its safe zones because a build
step removes them before the card is rendered, this file states its safe zones as
numbers in its header comment and respects them in the layout:

```
critical content   x from 300 to 1200, y from 60 to 380
everything else    may be cropped, overlaid or covered
```

Those bounds come from what the platforms do rather than from a preference. X
displays a 1500 × 500 header at roughly 1500 × 421, so the bottom 79 units are
gone, and then draws the avatar over the lower left. LinkedIn crops a 3:1 band
out of whatever it is given, which for 1500 wide is 500 tall and so happens to
match. Facebook scales down to 820 × 312 on a desktop and 640 × 360 on a phone.
Content inside the box above survives all of them.

The two decorative vesica marks bleed off the left and right edges and reach
twelve units below the critical band. That is intended, and it is the same rule
the OG card applies: decoration may be cropped, content may not.

## One banner, not three

1500 × 500 serves X and Mastodon directly and LinkedIn after its own crop.
Facebook's cover wants 1640 × 856, which is a different aspect ratio and would
need a second file. That file does not exist here on purpose: two banners drift,
and a profile header is looked at for about a second. If a campaign genuinely
needs a Facebook-sized cover, build it from the same masters and do not commit it
as a variant of this one.

## The descriptor has to match the rest of the repository

The line under the lockup — *Software for parishes, dioceses and the families
they serve* — is the same string used in `README.md` and in
`guidelines/brand-guidelines.md`. Change all three in one commit. A banner that
describes the product differently from the repository that ships it is a small
inconsistency that reads as a large one from outside.
