# Raster exports — PNG

Nothing in this directory is committed. Every file here is generated from an SVG
master by CI and uploaded as a workflow artefact, so a fresh clone finds this
directory containing only this README. That is the correct state and not a failed
build.

Generate them locally with:

```bash
pip install -r tools/requirements.txt   # needs Cairo: apt-get install libcairo2
python3 tools/build_exports.py --raster
```

## Why the PNGs are not committed

The SVG masters in `assets/logo/master/` are the only source of the mark. A
committed PNG is a second copy of that mark, and two copies of a logo can
disagree — somebody edits the master, the PNG keeps the old geometry, and the
disagreement is discovered by whoever downloads the stale file rather than by
whoever caused it. Keeping the rasters out of git makes the SVG the only place a
change can be made.

## What this directory contains after a build

Nine files: three masters at three densities.

| File | Pixels wide | Source master |
| --- | --- | --- |
| `viavitae-logo-vertical@1x.png` | 730 | `viavitae-logo-vertical.svg` |
| `viavitae-logo-vertical@2x.png` | 1460 | `viavitae-logo-vertical.svg` |
| `viavitae-logo-vertical@3x.png` | 2190 | `viavitae-logo-vertical.svg` |
| `viavitae-logo-horizontal@1x.png` | 1000 | `viavitae-logo-horizontal.svg` |
| `viavitae-logo-horizontal@2x.png` | 2000 | `viavitae-logo-horizontal.svg` |
| `viavitae-logo-horizontal@3x.png` | 3000 | `viavitae-logo-horizontal.svg` |
| `viavitae-logomark@1x.png` | 512 | `viavitae-logomark.svg` |
| `viavitae-logomark@2x.png` | 1024 | `viavitae-logomark.svg` |
| `viavitae-logomark@3x.png` | 1536 | `viavitae-logomark.svg` |

The width of each file is the master's own `viewBox` width multiplied by the
density, so a `@1x` PNG is the lockup at its natural size and never has to be
scaled by the thing that consumes it.

## Three densities, which are also three print resolutions

`@1x`, `@2x` and `@3x` are device pixel ratios: a standard display, a retina
phone or laptop, and the highest ratio in common use. Serving one `@2x` file to
a `@1x` display costs four times the bytes for no visible gain; serving `@1x` to
a `@3x` display makes the mark visibly soft on the newest hardware in the room,
which for a parish front desk is often the hardware that was bought last month.

The same three files also carry embedded resolution metadata of 72, 144 and 300
dpi respectively, written into the PNG `pHYs` chunk. A browser ignores that
chunk entirely, so nothing changes on screen; a print application reads it, so
the `@3x` file can be dropped into a poster layout and placed at a known
physical size instead of being guessed at. One file serves both readings, which
is why the density suffixes and the dpi figures are the same three numbers.

## What is not here

No `.ico`, no CMYK variant, and no EPS or PDF. The vector masters cover the
print and cutter workflows directly — a vinyl cutter and a laser engraver both
read SVG path data and neither reads a raster — and an `.ico` is a container of
rasters at sizes this directory already produces. If a consumer needs a specific
format that is missing, the answer is to add a step to
`tools/build_exports.py` and a row to the table above, not to commit a one-off
export that nothing regenerates.
