# Liturgical imagery

Real photography of real places, for a product whose users are parishes,
dioceses, funeral directors and the families they serve. This directory is a
committed brand asset library: unlike the rasters under `assets/logo/`, the files
here are **not** generated, so they **are** in git, and `.gitignore` deliberately
does not exclude them.

That decision has a reason worth stating, because it is the opposite of the one
made for the logo exports. A licence record that points at a file which is not in
the repository is not a licence record. If the photography were generated or
fetched at build time, this README would assert provenance and rights for images
nobody could inspect, and the assertion would be unverifiable exactly when it
mattered — during a takedown request or a licence audit.

## The licence record is the point of this file

Every image committed here must appear in the table below with its licence, its
source and its attribution requirement **before** the commit that adds it. Not
after. A photograph with an unresolved licence is not an asset, it is a liability
with a filename, and the moment it ships in a product the liability belongs to
whoever served it.

Permitted licences, and only these:

| Licence | May be used | Attribution required | Notes |
| --- | --- | --- | --- |
| Own work, copyright assigned to ViaVitae IT Technologies | yes | no | Preferred. Record the shoot date and the photographer. |
| CC0 1.0 | yes | no | Public domain dedication. Still record the source URL. |
| CC BY 4.0 | yes | **yes** | Attribution must be visible on the page that uses it, not only here. |
| CC BY-SA 4.0 | **no** | — | Share-alike would propagate to derivative layouts. Not accepted. |
| Any NC (non-commercial) variant | **no** | — | The product is commercial. |
| Stock licence, per-seat or per-impression | **no** | — | A per-impression licence cannot be honoured by a CDN. |
| Anything found by image search | **no** | — | Absence of a licence is not a licence. |

`.github/workflows/compliance-check.yml` asserts this file exists and that every
image file under this directory is named in it. It cannot verify that a licence
claim is true; it can verify that no image is shipped without one being made.

## Registry

No images are committed yet. This is the format each entry takes.

| File | Context | Licence | Source | Attribution | Shoot date |
| --- | --- | --- | --- | --- | --- |
| _(none yet)_ | | | | | |

## Directories

The six subdirectories are not an arbitrary taxonomy. Five of them sit on a
declared colour context in `tokens/colors.json` under `color.church.*` — four
distinct contexts, because basilica and cathedral share one — so the photography
and the palette of the page it sits on are chosen together rather than
separately:

| Directory | Colour context | Register |
| --- | --- | --- |
| `basilica/` | `color.church.basilica` | ceremonial, navy and gold |
| `cathedral/` | `color.church.basilica` | ceremonial — the token's own description names cathedral and heritage |
| `parish/` | `color.church.parish` | ordinary and warm, ivory and navy |
| `funeral/` | `color.church.funeral` | austere, no gold, no saturated accent |
| `cemetery/` | `color.church.cemetery` | stone and weathered bronze |
| `texture/` | none | material backgrounds, not a context |

`cathedral/` and `basilica/` share a colour context and are still separate
directories, because the buildings are not interchangeable to the people who use
them: a cathedral is a seat, a basilica is a designation, and a parish website
that calls its own church by the wrong one has made a factual error in the first
sentence a visitor reads. Keep them apart in the library so they stay apart in the
product.

`texture/` has no colour context because it is a material rather than a place —
marble, stonework, plaster, wood grain, used as a subtle background. Each file's
README states what it may be placed under and what it may not.

## Technical requirements

- **Format.** WebP preferred, JPEG accepted for photographs that WebP handles
  badly. No PNG for photography: the file is three to five times larger for no
  visible gain.
- **Size.** Under 2 MB per file, committed. A full-resolution archive belongs in
  object storage, not in git history, where it is retained by every clone forever
  whether or not anyone still needs it.
- **Long edge.** 2400px. That covers a full-bleed hero at 2x on a 1200px layout
  and nothing more; a 6000px master buys nothing a browser will display.
- **Alt text.** Every image needs a written description in the registry's
  attribution column or beside it in the consuming component. `guidelines/accessibility.md`
  carries the doctrine, including when an image is decorative and must carry an
  empty `alt` instead.
- **People.** A recognisable face requires a signed model release recorded in the
  registry, and for a funeral or a cemetery shoot, the written consent of the
  family. This is not a formality. Photography from a funeral is the single most
  sensitive asset class this product handles, and `docs/DPIA-template.md` covers
  the data-protection position.

## What must not go in here

- Screenshots of the product. Those belong in the consuming repository's docs,
  where they can be regenerated from the version they describe.
- Illustrations, icons or motifs. Those are `assets/imagery/motif/` or
  `tokens/icons.json`.
- Anything with a visible third-party logo, including a rival church-management
  product on a desk in the background of an otherwise good photograph.
- Anything with a recognisable face and no release on file.
