# Favicon and platform icon set

One file here is committed and five are generated.

| File | Status | Size | Source |
| --- | --- | --- | --- |
| `favicon.svg` | committed | 64 × 64 | itself — it is a master |
| `favicon-16.png` | generated | 16 × 16 | `favicon.svg` |
| `favicon-32.png` | generated | 32 × 32 | `favicon.svg` |
| `apple-touch-icon-180.png` | generated | 180 × 180 | `favicon.svg` |
| `android-chrome-192.png` | generated | 192 × 192 | `favicon.svg` |
| `android-chrome-512.png` | generated | 512 × 512 | `favicon.svg` |

Generate the PNGs with:

```bash
pip install -r tools/requirements.txt   # needs Cairo: apt-get install libcairo2
python3 tools/build_exports.py --favicon
```

## Why every size comes from the vector

Each PNG is rasterised from `favicon.svg` at its target resolution rather than
downscaled from a larger PNG. Downscaling a 512px raster to 16px averages the
artwork across the pixel grid and produces grey where the mark should be crisp;
rasterising the vector at 16px lets the rasteriser decide where the edges fall.
At icon sizes that decision is the difference between a mark and a smudge.

## Why these are not the logomark scaled down

`assets/logo/master/viavitae-logomark.svg` is monoline: a 32-unit stroke on a
512-unit artboard. At 16px that stroke is one device pixel, and one antialiased
pixel of stroke is grey. So `favicon.svg` is a separate master that keeps the
same vesica piscis geometry at exactly one tenth scale — every coordinate is the
logomark's with the decimal point moved — but draws it **filled** rather than
stroked, on an opaque navy plate. Same construction, different optical
correction, which is the standard practice for an icon that has to survive 16px.

The plate is opaque because a favicon is composited over browser chrome the brand
does not control: light in one theme, near black in the other. No single artwork
colour passes contrast against both, so the file supplies its own ground. Ivory
on navy-900 is 15.37:1.

## Wiring it up

Put the SVG last so it wins in the browsers that support it:

```html
<link rel="icon" href="/favicon-16.png" sizes="16x16" type="image/png">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon-180.png">
<link rel="manifest" href="/site.webappmanifest">
```

```json
{
  "name": "ViaVitae",
  "short_name": "ViaVitae",
  "icons": [
    { "src": "/android-chrome-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/android-chrome-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "theme_color": "#0E1B3D",
  "background_color": "#0E1B3D",
  "display": "standalone"
}
```

`theme_color` and `background_color` are both navy-900 so an installed app opens
on the plate colour rather than flashing white before the first paint. The values
come from `color.semantic.dark.surface.page` and `color.palette.navy.900` in
`tokens/colors.json`; do not hardcode them elsewhere.

## What is deliberately not here

**No `favicon.ico`.** An `.ico` is a container of rasters at 16, 32 and 48 pixels,
and the browsers that need it are the ones this brand does not support: Internet
Explorer 11, which reached end of support in June 2022, and legacy Edge. Every
browser in the supported set reads either `favicon.svg` or a PNG. `.gitignore`
excludes `*.ico` so a stray one cannot be committed by accident. If the support
floor ever changes, add an `.ico` step to `tools/build_exports.py` rather than
committing a file nothing regenerates.

**No `mstile-150.png` or `browserconfig.xml`.** Those are Windows 8 and 10
live-tile artefacts for the same browsers. Same reasoning, same answer.

**No 48px PNG.** Nothing requests it that does not also accept the SVG.
