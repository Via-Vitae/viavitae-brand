#!/usr/bin/env python3
"""Build the distributable artefacts of the ViaVitae brand system.

Four kinds of output come out of this script, and they are in one place because
they share a source and a failure mode. Every artefact here is derived from
something committed under ``tokens/`` or ``assets/``; none of them is authored.
An artefact that is authored twice is an artefact that disagrees with itself, and
the disagreement is always found by a consumer rather than by a reviewer.

    --figma     sync build/figma-tokens/tokens.json from tokens/*.json
    --raster    rasterise the logo masters to PNG and WebP
    --favicon   build the favicon and touch-icon set from the logomark
    --og        export the default Open Graph card
    --fonts     subset Fraunces and Inter to the shipped weights and write WOFF2
    --check     verify the SVG masters and the committed artefacts

``--check`` is the CI gate and needs no third-party package: it parses every SVG
as XML, asserts the geometry a logo or icon master must have, confirms the
committed derived files exist, and confirms each raster directory carries the
README explaining what lands in it. Whether those files hold the RIGHT values is
``tools/validate_tokens.py``'s job, which compares values rather than
timestamps. The raster paths need Cairo and the font path needs fontTools; both
are guarded, both say plainly what is missing and how to install it, and neither
fails silently by writing a placeholder a reviewer might mistake for the artefact.

Usage
-----
    python3 tools/build_exports.py --check              # CI
    python3 tools/build_exports.py --figma              # resync Figma tokens
    python3 tools/build_exports.py --raster --favicon --og
    python3 tools/build_exports.py --all
    python3 tools/build_exports.py --all --dry-run      # report, write nothing

Exit codes
----------
    0  every requested step succeeded
    1  a step failed: a malformed SVG, a stale artefact, a drifted token
    2  a step could not run: a missing dependency or a missing source file
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import defusedxml.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The token model — which source path maps to which derived path — lives in
# validate_tokens.py, because that script is the gate that asserts the mapping
# holds and this one is the tool that applies it. Duplicating the table here
# would create two definitions of "where does this token go", and the moment they
# diverge the exporter writes a file the validator rejects.
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from validate_tokens import (
        FIGMA_FILE,
        FIGMA_ONLY_COLOURS,
        TOKENS_CSS,
        Json,
        TokenError,
        as_int,
        figma_path_for,
        load_json_strict,
        load_token_namespace,
        studio_literal,
        substitute,
    )
    from validate_tokens import Report as ValidationReport
except ImportError as exc:  # pragma: no cover
    print(
        f"build_exports: cannot import validate_tokens from the same directory: {exc}",
        file=sys.stderr,
    )
    sys.exit(2)

# The three optional dependencies below carry a BARE `# type: ignore` with no
# error code, and that is deliberate rather than sloppy. Each is absent on a
# machine without Cairo or fontTools and present but untyped on one with them, so
# the error mypy raises on the import line is `import-not-found` in the first
# case and `import-untyped` in the second. Naming either code makes the ignore
# wrong in the other environment, and `--strict` turns a wrong code into an
# "unused ignore" error — so a specific code here would pin the file to whichever
# environment it happened to be written in. A bare ignore is used in both.
try:  # pragma: no cover - exercised only on a host with Cairo
    import cairosvg  # type: ignore
except ImportError:  # pragma: no cover
    cairosvg = None

try:  # pragma: no cover
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    Image = None

try:  # pragma: no cover
    from fontTools import subset as ftsubset  # type: ignore
except ImportError:  # pragma: no cover
    ftsubset = None

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
EDITOR_NS = {
    "http://www.inkscape.org/namespaces/inkscape",
    "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "http://www.bohemiancoding.com/sketch/ns",
    "http://ns.adobe.com/AdobeIllustrator/10.0/",
    "http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/",
    "http://www.figma.com/figma/ns",
}

#: Root font size the Figma conversions assume. Figma Variables carry no unit, so
#: a rem value has to become a pixel value, and 16px is the browser default and
#: the value ``build/css/reset.css`` preserves by setting ``font-size: 100%``.
ROOT_FONT_SIZE_PX = 16


def comment_hyphen_offence(source: str) -> int | None:
    """The line of the first double hyphen inside an XML comment, if there is one.

    XML forbids ``--`` anywhere between the comment delimiters, which means a
    comment cannot quote a command-line flag literally: writing ``build_exports.py
    --check`` in an SVG header makes the whole document not well-formed. The
    parser reports this as a bare ``not well-formed`` position with no cause, and
    the author has usually moved on by the time CI says so, which is how a
    one-character defect turns into an afternoon.

    This scans the raw text rather than the parsed tree because a file carrying
    the defect does not parse, so there is no tree to scan. It is a heuristic and
    is documented as one: it finds the first ``<!--``, then the first ``-->``
    after it, then looks for ``--`` in between. A comment whose content ends in a
    hyphen (``--->``) is a different and much rarer malformation, and this
    function will not name it.
    """
    index = 0
    while True:
        start = source.find("<!--", index)
        if start < 0:
            return None
        end = source.find("-->", start + 4)
        if end < 0:
            return None
        if "--" in source[start + 4 : end]:
            return source.count("\n", 0, start) + 1
        index = end + 3


# ---------------------------------------------------------------------------
# Outcome reporting
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """What a step did. ``skipped`` is distinct from ``failed`` on purpose.

    A missing system library is not a broken build, and reporting it as one
    teaches a contributor to ignore red output. It is reported as a skip naming
    the install command, which is actionable, and ``--check`` still fails if the
    artefact that library would have produced is absent or stale.
    """

    step: str
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def need(module: Any, name: str, install: str, outcome: Outcome) -> bool:
    """Record a skip and return False when an optional dependency is absent."""
    if module is not None:
        return True
    outcome.skipped.append(f"{name} is not installed; run: {install}")
    return False


# ---------------------------------------------------------------------------
# SVG masters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SvgMaster:
    """One committed SVG and the geometry it is required to have."""

    path: str
    role: str
    width: int
    height: int


#: Every SVG master, with the intrinsic size it must declare. A logo exported at
#: the wrong aspect ratio is not a small error: it is the mark, and it propagates
#: to every favicon, avatar, card and construction diagram derived from it.
#:
#: The dimensions are not arbitrary, but they are not all the same kind of
#: number. For THE TWO LOCKUPS the artboard is the ink's bounding box plus the
#: clear space the brand requires on all four sides, so a consumer who places
#: either file edge to edge with another element has respected the clear-space
#: rule without reading it. That margin is 50 units against the wordmark's
#: 100-unit cap height — half the cap height, stated in guidelines/logo-usage.md
#: and drawn in viavitae-logo-clearspace.svg. It is measured to the ink rather
#: than to the path data, because a round cap or join projects half a stroke
#: width past its coordinate; both lockups are positioned so the projection
#: lands on the boundary, which is why the stacked one is 424 tall rather than a
#: rounder 400.
#:
#: The other masters are sized by their own job: the logomark is 512 square
#: because it is the master everything else is scaled from, the favicon is 64
#: square because that is what the icon pipeline wants, the two construction
#: sheets are 1200 by 800 because they carry annotation, the OG card and the
#: social banner are the dimensions the platforms specify, and the motif and the
#: tile are squares chosen so the geometry lands on exact coordinates.
SVG_MASTERS: tuple[SvgMaster, ...] = (
    SvgMaster(
        "assets/logo/master/viavitae-logo-vertical.svg",
        "primary stacked lockup",
        730,
        424,
    ),
    SvgMaster(
        "assets/logo/master/viavitae-logo-horizontal.svg",
        "primary inline lockup",
        1000,
        200,
    ),
    SvgMaster("assets/logo/master/viavitae-logomark.svg", "mark only", 512, 512),
    SvgMaster(
        "assets/logo/monochrome/viavitae-logo-mono-black.svg",
        "one-colour black",
        1000,
        200,
    ),
    SvgMaster(
        "assets/logo/monochrome/viavitae-logo-mono-white.svg",
        "one-colour white",
        1000,
        200,
    ),
    SvgMaster(
        "assets/logo/inverse/viavitae-logo-inverse-navy.svg",
        "ivory on a dark ground",
        1000,
        200,
    ),
    SvgMaster(
        "assets/logo/inverse/viavitae-logo-inverse-gold.svg",
        "gold on a dark ground",
        1000,
        200,
    ),
    SvgMaster(
        "assets/logo/construction/viavitae-logo-construction.svg",
        "construction grid",
        1200,
        800,
    ),
    SvgMaster(
        "assets/logo/construction/viavitae-logo-clearspace.svg",
        "clear space",
        1200,
        800,
    ),
    SvgMaster("assets/favicon/favicon.svg", "modern favicon", 64, 64),
    SvgMaster("assets/og/og-template-1200x630.svg", "OG template", 1200, 630),
    SvgMaster("assets/social/banner-1500x500.svg", "social banner", 1500, 500),
    SvgMaster("assets/imagery/motif/ichthys-geometry.svg", "motif master", 512, 512),
    SvgMaster("assets/imagery/motif/pattern-tile.svg", "repeating tile", 256, 256),
)

#: Elements an SVG master must not carry. ``metadata`` is editor residue that
#: inflates the file and leaks the authoring tool and sometimes a local file path.
#: The rest are forbidden because a logo master must be flat geometry that every
#: renderer, converter and cutter interprets identically: a clip path or a mask
#: is honoured by a browser, approximated by a rasteriser and ignored by a vinyl
#: cutter, and a filter has no meaning at all outside a browser.
FORBIDDEN_SVG_ELEMENTS = frozenset(
    {
        f"{{{SVG_NS}}}metadata",
        f"{{{SVG_NS}}}clipPath",
        f"{{{SVG_NS}}}mask",
        f"{{{SVG_NS}}}filter",
        f"{{{SVG_NS}}}foreignObject",
        f"{{{SVG_NS}}}script",
        f"{{{SVG_NS}}}image",
        "metadata",
        "clipPath",
        "mask",
        "filter",
        "foreignObject",
        "script",
        "image",
    }
)

#: Raster outputs derived from a master, as (suffix, pixel multiplier, dpi).
#:
#: The suffix is a device pixel ratio and the dpi is the same three numbers
#: expressed the way a print workflow wants them: 1x is 72dpi, 2x is 144dpi and
#: 3x is 300dpi. Both readings are true of one file. A PNG's dpi lives in the
#: pHYs chunk and a browser ignores it, so on screen these are simply 1x, 2x and
#: 3x; a print shop opening the same file sees a resolution it can place a
#: poster from. Writing only one of the two would leave either the web or the
#: parish newsletter guessing which file it was supposed to take.
RASTER_WIDTHS: tuple[tuple[str, int, int], ...] = (
    ("@1x", 1, 72),
    ("@2x", 2, 144),
    ("@3x", 3, 300),
)

#: The inline lockup and its four single-colour variants. The variants differ
#: from the master in exactly one respect — the colour the artwork is drawn in —
#: and in nothing else. That invariant is worth asserting, because the failure it
#: prevents is invisible in review: somebody edits the master, forgets the
#: variants, and the brand now has five slightly different logotypes in
#: circulation, which is precisely what a logo repository exists to prevent.
LOCKUP_MASTER = "assets/logo/master/viavitae-logo-horizontal.svg"
LOCKUP_VARIANTS: tuple[str, ...] = (
    "assets/logo/monochrome/viavitae-logo-mono-black.svg",
    "assets/logo/monochrome/viavitae-logo-mono-white.svg",
    "assets/logo/inverse/viavitae-logo-inverse-navy.svg",
    "assets/logo/inverse/viavitae-logo-inverse-gold.svg",
)

#: Every colour a single-colour lockup variant is permitted to use, with the
#: ground it is for. Asserting membership stops a variant appearing in a colour
#: nobody has measured, which is how a lockup ends up at 2.2:1 on a page.
PERMITTED_LOCKUP_COLOURS: dict[str, str] = {
    "#0E1B3D": "navy-900, the primary, for a light ground",
    "#000000": "process black, for a one-ink reproduction",
    "#FFFFFF": "process white, for a one-ink reproduction on a dark ground",
    "#F7F4EC": "ivory-100, the inverse for a navy ground — 15.37:1",
    "#C9A227": "gold-500, the ceremonial inverse for a navy ground — 6.98:1",
}


def path_data(root: ET.Element) -> list[str]:
    """Every ``d`` attribute under ``root``, in document order."""
    return [
        element.attrib["d"]
        for element in root.iter()
        if element.tag in (f"{{{SVG_NS}}}path", "path") and "d" in element.attrib
    ]


def paint_colours(root: ET.Element) -> set[str]:
    """Every literal colour the artwork is painted in, normalised to uppercase."""
    found: set[str] = set()
    for element in root.iter():
        for attribute in ("fill", "stroke"):
            value = element.attrib.get(attribute, "").strip()
            if value.startswith("#"):
                found.add(value.upper())
    return found


def check_lockup_variants(roots: Mapping[str, ET.Element], outcome: Outcome) -> None:
    """Assert the single-colour variants are the master with a different paint.

    Two things are compared. The path data must be identical, in order and
    character for character, because a variant that has drifted geometrically is
    a second logotype rather than a colour of the first. The paints must all be
    in the permitted set, because a colour nobody has measured against a ground
    is a contrast failure waiting to be discovered by a user.

    Takes the already-parsed roots rather than reading the files again, so a
    malformed master is reported once by :func:`parse_svg` and not once more
    here.
    """
    master_root = roots.get(LOCKUP_MASTER)
    if master_root is None:
        return
    master_paths = path_data(master_root)
    if not master_paths:
        outcome.failures.append(f"{LOCKUP_MASTER} contains no path data")
        return
    for paint in sorted(paint_colours(master_root)):
        if paint not in PERMITTED_LOCKUP_COLOURS:
            outcome.failures.append(
                f"{LOCKUP_MASTER} paints in {paint}, which is not in "
                "PERMITTED_LOCKUP_COLOURS and has no measured ground"
            )

    for relative in LOCKUP_VARIANTS:
        variant_root = roots.get(relative)
        if variant_root is None:
            continue
        variant_paths = path_data(variant_root)
        if variant_paths != master_paths:
            if len(variant_paths) != len(master_paths):
                outcome.failures.append(
                    f"{relative} has {len(variant_paths)} paths against the master's "
                    f"{len(master_paths)}; a variant is the master in a different "
                    "colour and nothing else"
                )
            else:
                differing = [
                    index
                    for index, (a, b) in enumerate(zip(master_paths, variant_paths))
                    if a != b
                ]
                outcome.failures.append(
                    f"{relative} differs from {LOCKUP_MASTER} at path "
                    f"{', '.join(str(i) for i in differing)}; regenerate the variant "
                    "from the master rather than editing it separately"
                )
            continue
        paints = paint_colours(variant_root)
        if len(paints) != 1:
            outcome.failures.append(
                f"{relative} paints in {', '.join(sorted(paints))}; a one-colour "
                "variant uses exactly one colour, or it is not a one-colour variant"
            )
        for paint in sorted(paints):
            if paint not in PERMITTED_LOCKUP_COLOURS:
                outcome.failures.append(
                    f"{relative} paints in {paint}, which is not in "
                    "PERMITTED_LOCKUP_COLOURS and has no measured ground"
                )


def parse_svg(repo_root: Path, relative: str, outcome: Outcome) -> ET.Element | None:
    """Parse an SVG master and assert the geometry and hygiene rules."""
    path = repo_root / relative
    if not path.is_file():
        outcome.failures.append(f"{relative} is missing")
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        outcome.failures.append(f"{relative} is not valid UTF-8: {exc}")
        return None
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        outcome.failures.append(f"{relative} is not well-formed XML: {exc}")
        line = comment_hyphen_offence(source)
        if line is not None:
            outcome.failures.append(
                f"{relative} has a double hyphen inside the XML comment starting "
                f"on line {line}. XML forbids -- between the comment delimiters, "
                "so a command-line flag cannot be quoted in a comment literally; "
                "spell the step out in words"
            )
        return None

    if root.tag != f"{{{SVG_NS}}}svg":
        outcome.failures.append(f"{relative} has a root element of {root.tag}, not svg")
        return None

    for namespace in EDITOR_NS:
        if namespace in root.attrib or any(
            key.startswith(f"{{{namespace}}}") for key in root.attrib
        ):
            outcome.failures.append(
                f"{relative} carries editor metadata from {namespace}; re-export "
                "with metadata stripped"
            )

    viewbox = root.attrib.get("viewBox")
    if viewbox is None:
        outcome.failures.append(
            f"{relative} has no viewBox, so it has no intrinsic aspect ratio and "
            "scales to whatever container it lands in"
        )
        return None
    parts = viewbox.replace(",", " ").split()
    if len(parts) != 4:
        outcome.failures.append(
            f"{relative} viewBox {viewbox!r} does not have four components"
        )
        return None
    try:
        min_x, min_y, width, height = (float(part) for part in parts)
    except ValueError:
        outcome.failures.append(f"{relative} viewBox {viewbox!r} is not numeric")
        return None
    if min_x != 0.0 or min_y != 0.0:
        outcome.failures.append(
            f"{relative} viewBox starts at {min_x},{min_y}; a master is drawn from "
            "the origin so clear space is measured from the artboard edge"
        )
    if width <= 0 or height <= 0:
        outcome.failures.append(f"{relative} viewBox has a non-positive extent")
        return None

    declared = next((item for item in SVG_MASTERS if item.path == relative), None)
    if declared is not None:
        if (width, height) != (float(declared.width), float(declared.height)):
            outcome.failures.append(
                f"{relative} viewBox is {width:g}x{height:g} but the {declared.role} "
                f"master is specified at {declared.width}x{declared.height}"
            )
        for attribute in ("width", "height"):
            value = root.attrib.get(attribute)
            if value is not None:
                number = re.sub(r"(px|pt|em|rem)$", "", value.strip())
                try:
                    if float(number) != float(getattr(declared, attribute)):
                        outcome.failures.append(
                            f"{relative} {attribute}={value!r} disagrees with its "
                            f"viewBox and with the {declared.role} specification"
                        )
                except ValueError:
                    outcome.failures.append(
                        f"{relative} {attribute}={value!r} is not a length"
                    )

    title = root.find(f"{{{SVG_NS}}}title")
    if title is None:
        outcome.failures.append(
            f"{relative} has no <title>. An SVG inlined into a page has no "
            "accessible name without one, and an asset that is only usable as an "
            "<img src> with alt text is an asset that fails the moment a "
            "component inlines it for currentColor"
        )
    elif not (title.text or "").strip():
        outcome.failures.append(f"{relative} has an empty <title>")

    for element in root.iter():
        if element.tag in FORBIDDEN_SVG_ELEMENTS:
            name = element.tag.split("}")[-1]
            outcome.failures.append(
                f"{relative} contains a <{name}> element; masters are flat geometry "
                "with live strokes, and a clip path or filter changes what a "
                "consumer measures"
            )
        for key in element.attrib:
            if key.startswith("{") and key[1:].split("}")[0] in EDITOR_NS:
                outcome.failures.append(f"{relative} carries an editor attribute {key}")
            if key.startswith(f"{{{XLINK_NS}}}"):
                outcome.failures.append(
                    f"{relative} uses a deprecated xlink:href; SVG 2 uses href"
                )

    if root.find(f"{{{SVG_NS}}}script") is not None:
        outcome.failures.append(
            f"{relative} contains script; an asset must not execute"
        )
    return root


def check_og_guides(repo_root: Path, outcome: Outcome) -> None:
    """Assert the OG template's guide region exists and strips to valid XML.

    :func:`strip_guides` otherwise runs only when somebody asks for the card, so
    a template whose sentinels were deleted or moved would fail at export time —
    the one moment a failure is expensive, because it happens in CI on a release
    branch rather than on the commit that broke it. Checking it here moves the
    failure to the commit.

    This is one of the few checks in the file that can be exercised without
    Cairo, because it tests the text transformation rather than the rasteriser.
    """
    template = repo_root / OG_TEMPLATE
    if not template.is_file():
        return  # parse_svg has already reported the missing file
    try:
        source = template.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return  # parse_svg has already reported the encoding
    try:
        artwork = strip_guides(source)
    except GuidesError as exc:
        outcome.failures.append(str(exc))
        return
    if len(artwork) >= len(source):
        outcome.failures.append(
            f"{OG_TEMPLATE} strip removed nothing; the sentinel comments are "
            "present but there is no guide artwork between them"
        )
    try:
        root = ET.fromstring(artwork)
    except ET.ParseError as exc:
        outcome.failures.append(
            f"{OG_TEMPLATE} is not well-formed XML once its guide region is "
            f"stripped, so the exported card cannot be rendered: {exc}"
        )
        return
    if root.find(".//*[@id='guides']") is not None:
        outcome.failures.append(
            f"{OG_TEMPLATE} still contains an element with id 'guides' after "
            "stripping, so the safe-zone artwork would ship in og-default.png"
        )


def check_svgs(repo_root: Path, outcome: Outcome) -> None:
    """Validate every committed SVG master, then the invariants between them."""
    roots: dict[str, ET.Element] = {}
    for master in SVG_MASTERS:
        root = parse_svg(repo_root, master.path, outcome)
        if root is not None:
            roots[master.path] = root
    check_lockup_variants(roots, outcome)
    check_og_guides(repo_root, outcome)
    on_disk = (
        sorted(
            str(item.relative_to(repo_root))
            for item in (repo_root / "assets").rglob("*.svg")
        )
        if (repo_root / "assets").is_dir()
        else []
    )
    known = {master.path for master in SVG_MASTERS}
    for relative in on_disk:
        if relative not in known:
            outcome.failures.append(
                f"{relative} is an SVG with no entry in SVG_MASTERS, so nothing "
                "asserts its geometry; add it to the table in tools/build_exports.py"
            )


# ---------------------------------------------------------------------------
# Raster pipeline
# ---------------------------------------------------------------------------


def rasterise(
    repo_root: Path, source: str, target: Path, width: int, outcome: Outcome
) -> bool:
    """Rasterise one SVG to PNG at ``width`` pixels wide."""
    if not need(
        cairosvg,
        "cairosvg",
        "pip install -r tools/requirements.txt (and install Cairo: "
        "apt-get install libcairo2 on Debian and Ubuntu)",
        outcome,
    ):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        cairosvg.svg2png(
            url=str(repo_root / source),
            write_to=str(target),
            output_width=width,
            background_color=None,
        )
    except Exception as exc:  # noqa: BLE001 - cairosvg raises a bare Exception
        outcome.failures.append(f"{source} -> {target}: {exc}")
        return False
    outcome.written.append(str(target.relative_to(repo_root)))
    return True


def rasterise_text(
    repo_root: Path, svg: str, label: str, target: Path, width: int, outcome: Outcome
) -> bool:
    """Rasterise SVG held in memory rather than on disk.

    Exists for the one case where what gets drawn is not what is committed: the
    Open Graph card is exported from the template with its safe-zone guides
    removed. ``label`` names the committed file the text came from, so a failure
    points a reader at something they can open.
    """
    if not need(
        cairosvg,
        "cairosvg",
        "pip install -r tools/requirements.txt (and install Cairo: "
        "apt-get install libcairo2 on Debian and Ubuntu)",
        outcome,
    ):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=str(target),
            output_width=width,
            background_color=None,
        )
    except Exception as exc:  # noqa: BLE001 - cairosvg raises a bare Exception
        outcome.failures.append(f"{label} -> {target}: {exc}")
        return False
    outcome.written.append(str(target.relative_to(repo_root)))
    return True


def build_raster(repo_root: Path, outcome: Outcome, dry_run: bool) -> None:
    """Rasterise the logo masters to the PNG and WebP export sets.

    Three densities rather than one: 1x is what a browser on a standard display
    asks for, 2x is a retina phone and most laptops, and 3x is the largest common
    device pixel ratio. A single 2x export served to a 1x display is a file four
    times larger than it needs to be, and a 1x export served to a 3x display is
    the brand mark visibly soft on the newest hardware a parish is most likely to
    have bought for its front desk.
    """
    masters = (
        "assets/logo/master/viavitae-logo-vertical.svg",
        "assets/logo/master/viavitae-logo-horizontal.svg",
        "assets/logo/master/viavitae-logomark.svg",
    )
    declared = {item.path: item for item in SVG_MASTERS}
    for source in masters:
        master = declared[source]
        stem = Path(source).stem
        for suffix, multiplier, dpi in RASTER_WIDTHS:
            width = master.width * multiplier
            png = repo_root / "assets/logo/raster-exports/png" / f"{stem}{suffix}.png"
            if dry_run:
                outcome.written.append(f"{png.relative_to(repo_root)} (dry run)")
                continue
            if not rasterise(repo_root, source, png, width, outcome):
                continue
            if not need(
                Image, "pillow", "pip install -r tools/requirements.txt", outcome
            ):
                continue
            # Cairo writes a PNG with no pHYs chunk, which every print
            # application reads as 72dpi or as "unknown". Re-saving through
            # Pillow stamps the resolution the suffix already implies. ``copy()``
            # detaches the pixels from the open file handle so the save cannot
            # collide with the read.
            try:
                with Image.open(png) as handle:
                    frame = handle.copy()
                frame.save(png, "PNG", dpi=(dpi, dpi))
            except OSError as exc:
                outcome.failures.append(f"{png.name}: stamping {dpi} dpi failed: {exc}")
                continue
            webp = (
                repo_root / "assets/logo/raster-exports/webp" / f"{stem}{suffix}.webp"
            )
            webp.parent.mkdir(parents=True, exist_ok=True)
            try:
                with Image.open(png) as handle:
                    handle.save(webp, "WEBP", quality=90, method=6)
            except OSError as exc:
                outcome.failures.append(f"{png.name} -> {webp.name}: {exc}")
                continue
            outcome.written.append(str(webp.relative_to(repo_root)))


#: The favicon set, as (filename, pixel size, source master). Sizes are the ones
#: browsers actually request; a size nobody asks for is a file nobody serves.
#:
#: Every one of them comes from assets/favicon/favicon.svg and NOT from the
#: 512-unit logomark. That is a deliberate substitution and it is the reason the
#: favicon master exists: the logomark is monoline, and its 32-unit stroke on a
#: 512 artboard becomes one device pixel at 16px, which antialiases into a grey
#: smudge. The favicon master is the same vesica piscis geometry at exactly one
#: tenth scale, drawn FILLED, on an opaque navy plate. Rasterising a stroked
#: master at icon sizes produces an icon that is legible in the repository and
#: illegible in a browser tab.
FAVICON_TARGETS: tuple[tuple[str, int, str], ...] = (
    ("favicon-16.png", 16, "assets/favicon/favicon.svg"),
    ("favicon-32.png", 32, "assets/favicon/favicon.svg"),
    ("apple-touch-icon-180.png", 180, "assets/favicon/favicon.svg"),
    ("android-chrome-192.png", 192, "assets/favicon/favicon.svg"),
    ("android-chrome-512.png", 512, "assets/favicon/favicon.svg"),
)


def build_favicon(repo_root: Path, outcome: Outcome, dry_run: bool) -> None:
    """Build the icon set from the filled favicon master.

    Every size comes from the vector at the target resolution rather than from a
    downscaled raster, because downscaling a 512px PNG to 16px averages the
    artwork into grey. Rasterising the vector at 16px lets the rasteriser place
    the edge on the pixel grid instead.
    """
    for name, size, source in FAVICON_TARGETS:
        target = repo_root / "assets/favicon" / name
        if dry_run:
            outcome.written.append(f"assets/favicon/{name} (dry run)")
            continue
        if not rasterise(repo_root, source, target, size, outcome):
            continue
        if name.startswith("apple-touch-icon") and Image is not None:
            # iOS composites the icon onto a background of its own choosing and
            # ignores transparency, so an icon with a transparent field renders on
            # whatever the device picks. The favicon master already carries an
            # opaque navy plate, which makes this flattening redundant today; it
            # stays because the failure it prevents is invisible until somebody
            # ships an icon on a home screen, and because a future edit that
            # drops the plate would otherwise ship silently.
            try:
                with Image.open(target) as handle:
                    flat = Image.new("RGBA", handle.size, (14, 27, 61, 255))
                    flat.alpha_composite(handle.convert("RGBA"))
                    flat.convert("RGB").save(target, "PNG")
            except OSError as exc:
                outcome.failures.append(f"{name}: flattening failed: {exc}")


#: The Open Graph template carries its safe-zone guides as drawn artwork,
#: because a template whose margins a designer cannot see is not a template. The
#: exported card must not carry them, so the guides sit between two sentinel
#: comments and :func:`strip_guides` removes that region.
#:
#: Text surgery on XML is usually the wrong answer and is the right one here.
#: The region is delimited by markers this repository controls, both markers are
#: asserted present before anything is removed, and the result is re-parsed as
#: XML by :func:`check_svgs` so a malformed edit fails the build rather than the
#: export. The alternative — an ElementTree round trip — silently discards every
#: comment in the file, including the rationale the template exists to carry.
GUIDES_BEGIN = "<!-- GUIDES:BEGIN -->"
GUIDES_END = "<!-- GUIDES:END -->"
OG_TEMPLATE = "assets/og/og-template-1200x630.svg"


class GuidesError(ValueError):
    """The OG template's guide region is missing or malformed."""


def strip_guides(source: str) -> str:
    """Remove the sentinel-delimited guide region from the OG template.

    Whole lines are removed rather than the exact span, so no blank line is left
    behind to make the exported source differ from the committed one by
    whitespace.
    """
    start = source.find(GUIDES_BEGIN)
    end = source.find(GUIDES_END)
    if start < 0 and end < 0:
        raise GuidesError(
            f"{OG_TEMPLATE} carries neither {GUIDES_BEGIN} nor {GUIDES_END}, so "
            "there is no guide region to strip; either the guides were removed "
            "by hand or they were never marked"
        )
    if start < 0 or end < 0:
        missing = GUIDES_BEGIN if start < 0 else GUIDES_END
        raise GuidesError(
            f"{OG_TEMPLATE} carries one guide sentinel but not {missing}, so the "
            "guide region has no reliable boundary"
        )
    if end < start:
        raise GuidesError(
            f"{OG_TEMPLATE} has {GUIDES_END} before {GUIDES_BEGIN}; the sentinels "
            "are the wrong way round"
        )
    line_start = source.rfind("\n", 0, start) + 1
    line_end = source.find("\n", end)
    line_end = len(source) if line_end < 0 else line_end + 1
    return source[:line_start] + source[line_end:]


def build_og(repo_root: Path, outcome: Outcome, dry_run: bool) -> None:
    """Export the default Open Graph card at 1200x630, guides stripped."""
    target = repo_root / "assets/og/og-default.png"
    if dry_run:
        outcome.written.append("assets/og/og-default.png (dry run)")
        return
    template = repo_root / OG_TEMPLATE
    if not template.is_file():
        outcome.failures.append(f"{OG_TEMPLATE} is missing")
        return
    try:
        artwork = strip_guides(template.read_text(encoding="utf-8"))
    except GuidesError as exc:
        outcome.failures.append(str(exc))
        return
    except UnicodeDecodeError as exc:
        outcome.failures.append(f"{OG_TEMPLATE} is not valid UTF-8: {exc}")
        return
    rasterise_text(repo_root, artwork, OG_TEMPLATE, target, 1200, outcome)


#: Social avatar, exported from the filled favicon master at the largest size
#: the platforms accept so that each one downscales rather than upscales. The
#: master's opaque plate matters here more than anywhere else: a platform crops
#: an avatar to a circle it chooses the size of, over a background it chooses the
#: colour of, and a transparent mark survives neither decision. The artwork sits
#: inside the circle inscribed in the plate — its furthest corner is 24.2 units
#: from the centre of a 32-unit radius — so the crop takes the plate's corners
#: and none of the mark.
AVATAR_TARGET = ("assets/social/avatar-400.png", 400, "assets/favicon/favicon.svg")


def build_social(repo_root: Path, outcome: Outcome, dry_run: bool) -> None:
    name, size, source = AVATAR_TARGET
    target = repo_root / name
    if dry_run:
        outcome.written.append(f"{name} (dry run)")
        return
    rasterise(repo_root, source, target, size, outcome)


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


#: Derived files that ARE committed, so their absence is a defect. The Figma
#: token file and the CSS custom properties are consumed directly from the
#: repository, which is what makes them committed. ``build/css/reset.css`` is
#: deliberately NOT here: it is authored, not derived, and consumes tokens
#: through ``var()`` at runtime rather than embedding their values.
COMMITTED_DERIVED: tuple[str, ...] = (FIGMA_FILE, TOKENS_CSS)

#: Directories that hold derived rasters. Every raster is excluded by .gitignore
#: on the principle that a PNG is a second copy of a mark whose SVG is the only
#: source, so a fresh clone legitimately has none of them and an empty directory
#: is the correct state rather than a failure. Each keeps a committed README.md
#: naming the files that land in it, and the README's presence is what is checked.
RASTER_DIRS: tuple[str, ...] = (
    "assets/logo/raster-exports/png",
    "assets/logo/raster-exports/webp",
    "assets/favicon",
    "assets/og",
    "assets/social",
)


def check_artefacts(repo_root: Path, outcome: Outcome) -> None:
    """Confirm the committed artefacts exist and the raster directories explain themselves.

    This deliberately does NOT compare modification times. An mtime check looks
    like a currency check and is not one: a fresh clone gives every file the
    checkout timestamp, so the comparison is meaningless exactly where it would be
    run, and editing a ``$description`` in a token file makes a stylesheet look
    stale without changing a single value it carries. A gate that cries stale on
    every documentation edit is a gate that gets ``|| true`` appended to it.

    Currency is instead checked by value, in ``tools/validate_tokens.py``, which
    resolves every token and compares it against the CSS custom properties and the
    Figma copy. That check does not care when anything was written and cannot be
    satisfied by touching a file.
    """
    for relative in COMMITTED_DERIVED:
        path = repo_root / relative
        if not path.is_file():
            outcome.failures.append(
                f"{relative} is committed and derived but does not exist; run "
                "python3 tools/build_exports.py --figma"
            )
        elif path.stat().st_size == 0:
            outcome.failures.append(f"{relative} is empty")

    for relative in RASTER_DIRS:
        directory = repo_root / relative
        if not directory.is_dir():
            outcome.failures.append(f"{relative} does not exist as a directory")
            continue
        readme = directory / "README.md"
        if not readme.is_file():
            outcome.failures.append(
                f"{relative} has no README.md; its contents are gitignored rasters, "
                "so the README is the only thing telling a contributor what is "
                "supposed to be there and how to produce it"
            )


# ---------------------------------------------------------------------------
# Figma token sync
# ---------------------------------------------------------------------------

#: Source tokens that are deliberately not expressed as a Figma number, mapped
#: to the Figma path a naive conversion would look for. ``radius.circle`` is a
#: percentage: Figma's corner radius is a float in pixels, and a circle is not a
#: radius at all but a radius equal to half the element's own size, which no
#: variable can hold. Exporting 50 as a radius would produce a 50px corner on a
#: 24px avatar. The consuming component sets ``border-radius: 50%`` directly.
PERCENTAGE_SOURCES: dict[str, str] = {"radius.circle": "global.radius.circle"}

#: Figma's own weight names. Tokens Studio matches a font style by NAME rather
#: than by number, so a variable font at 600 has to be written as "Semi Bold" —
#: the two-word form the family actually uses — and not as "Semibold" or "600".
FIGMA_WEIGHT_NAMES: dict[int, str] = {
    100: "Thin",
    200: "Extra Light",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "Semi Bold",
    700: "Bold",
    800: "Extra Bold",
    900: "Black",
}


#: A NON-TOKEN leaf object is collapsed onto one line only if it stays under this
#: width. Without the limit, ``$themes[].selectedTokenSets`` — nine scalar
#: entries and no meaning read as a single line — becomes 240 characters wide.
#: Tokens themselves are always collapsed, at any length; see ``dump_studio``.
MAX_INLINE_WIDTH = 140


def _is_leaf(node: Any) -> bool:
    return isinstance(node, Mapping) and all(
        not isinstance(value, (Mapping, list)) for value in node.values()
    )


def _is_token(node: Any) -> bool:
    """True for a Tokens Studio leaf: an object carrying both ``value`` and ``type``."""
    return isinstance(node, Mapping) and "value" in node and "type" in node


def _inline(node: Mapping) -> str:
    """Render a leaf object on one line, with spaces inside the braces.

    The spacing is not decoration: a file of 500 tokens where each line begins
    ``{"value"`` reads as a wall, and the space is what lets the eye find the key.
    ``json.dumps`` does not offer it, so the two brace characters are added here.
    """
    body = json.dumps(dict(node), ensure_ascii=False, separators=(", ", ": "))
    return "{ " + body[1:-1] + " }"


def dump_studio(node: Any, level: int = 0) -> str:
    """Serialise a Tokens Studio document with leaf objects collapsed to one line.

    ``json.dump(indent=2)`` would expand every token to four or five lines and
    take this file from readable to searchable-only. A generated file still has
    to be reviewed, and a reviewer comparing a design token against a diff line
    needs the whole token on that line. Output is deterministic — insertion order
    preserved, no trailing whitespace, one newline at the end — so a sync that
    changes nothing produces an empty diff, which is the property that makes
    "the generated file is committed and current" checkable in CI.
    """
    pad = "  " * level
    if isinstance(node, Mapping):
        if not node:
            return "{}"
        if _is_leaf(node):
            # A token is always collapsed, however long its description: the
            # description is precisely what a reviewer reads on the diff line.
            # A non-token leaf is collapsed only if it stays narrow, so a block
            # like $themes[].selectedTokenSets — nine scalar entries and no
            # meaning as one line — is still expanded.
            #
            # Rendered once and bound, because the width test and the return both
            # want the same string and rendering it twice would serialise the
            # node twice for every leaf in a 500-token file.
            inline = _inline(node)
            if _is_token(node) or len(inline) + len(pad) <= MAX_INLINE_WIDTH:
                return inline
        items: list[str] = []
        for position, (key, value) in enumerate(node.items()):
            rendered = dump_studio(value, level + 1)
            # A blank line before each multi-line child at the two shallowest
            # levels, which is how a reader separates one token group from the
            # next in a format that cannot carry section comments.
            separator = "\n" if position and level < 2 and rendered[0] in "{[" else ""
            items.append(
                f"{separator}{pad}  {json.dumps(str(key), ensure_ascii=False)}: {rendered}"
            )
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(node, list):
        if not node:
            return "[]"
        entries = [f"{pad}  {dump_studio(value, level + 1)}" for value in node]
        return "[\n" + ",\n".join(entries) + "\n" + pad + "]"
    return json.dumps(node, ensure_ascii=False)


def px_to_number(value: Any) -> str | None:
    """``"16px"`` to ``"16"``. Figma Variables are unitless floats."""
    number = as_int(value)
    return None if number is None else str(number)


def resolve_source(
    tokens: Mapping[str, Json], report: ValidationReport
) -> dict[str, Any]:
    """Resolve every token in the source namespace to a literal value."""
    resolved: dict[str, Any] = {}
    for path, token in sorted(tokens.items()):
        try:
            resolved[path] = substitute(token.get("$value"), tokens, (path,))
        except TokenError as exc:
            report.fail("alias", path, f"cannot resolve for export: {exc}")
    return resolved


def sync_figma(repo_root: Path, dry_run: bool, outcome: Outcome) -> None:
    """Rewrite the value fields of the Figma token file from the token sources.

    Only ``value`` fields are touched. The set structure, the ``$themes`` block,
    the ``$metadata`` ordering and every ``$description`` are preserved exactly,
    because those carry design-facing prose that is written for a reader in Figma
    and is not derivable from the source. What IS derivable is every number and
    every colour, and those are the things that drift.

    The typography block is verified rather than rewritten: its values are a
    lossy conversion (rem to px at a 16px root, a unitless multiplier to a pixel
    line height, an em to a pixel tracking) and a conversion that disagrees with
    its rule is a defect in one of the two, not something to paper over by
    regenerating one from the other.
    """
    report = ValidationReport()
    tokens = load_token_namespace(repo_root, report)
    source = resolve_source(tokens, report)
    for failure in report.failures:
        outcome.failures.append(f"{failure.location}: {failure.message}")
    if not tokens:
        outcome.failures.append("no tokens could be loaded; nothing to sync from")
        return

    path = repo_root / FIGMA_FILE
    try:
        document = load_json_strict(path)
    except TokenError as exc:
        outcome.failures.append(str(exc))
        return

    index: dict[str, Any] = {}

    def walk(node: Any, prefix: str) -> None:
        if not isinstance(node, Mapping):
            return
        if "value" in node and "type" in node:
            if prefix:
                index[prefix] = node
            return
        for key, child in node.items():
            if key.startswith("$"):
                continue
            walk(child, f"{prefix}.{key}" if prefix else key)

    walk(document, "")

    changes = 0

    def current(node: Any) -> Any:
        """The node's value with any Figma alias resolved.

        Comparing raw strings would flatten ``{global.color.navy.900}`` into a
        literal, and that is the one edit this sync must never make: a Figma
        Variable that holds a literal instead of an alias stops responding to a
        mode switch, so the dark theme silently keeps the light colour. The alias
        IS the feature. Only a genuinely different resolved value is a drift.
        """
        return studio_literal(node, index)

    colour_paths: dict[str, str] = {}
    for token_path in source:
        target = figma_path_for(token_path)
        if target is not None and token_path.startswith(
            (
                "color.palette.",
                "color.semantic.",
                "color.church.",
                "season.",
                "color.chart.",
            )
        ):
            colour_paths[target] = token_path
    for figma_path, source_path in FIGMA_ONLY_COLOURS:
        colour_paths[figma_path] = source_path

    for figma_path, source_path in sorted(colour_paths.items()):
        node = index.get(figma_path)
        if node is None:
            continue
        if tokens.get(source_path, {}).get("$type") != "color":
            continue
        wanted = source.get(source_path)
        if not isinstance(wanted, str):
            continue
        if str(current(node)).upper() != wanted.upper():
            node["value"] = wanted
            changes += 1

    for name in (
        "instant",
        "immediate",
        "fast",
        "base",
        "moderate",
        "slow",
        "deliberate",
        "ceremonial",
    ):
        node = index.get(f"motion.duration.{name}")
        value = source.get(f"duration.{name}")
        if node is None or not isinstance(value, str):
            continue
        match = re.fullmatch(r"([\d.]+)ms", value)
        if match and str(current(node)) != str(int(float(match.group(1)))):
            node["value"] = str(int(float(match.group(1))))
            changes += 1
    node = index.get("motion.duration.reduced-motion")
    value = source.get("reducedMotion.duration")
    if node is not None and isinstance(value, str):
        match = re.fullmatch(r"([\d.]+)ms", value)
        if match and str(current(node)) != str(int(float(match.group(1)))):
            node["value"] = str(int(float(match.group(1))))
            changes += 1

    for name, points in source.items():
        if not name.startswith("easing.") or not isinstance(points, list):
            continue
        node = index.get(f"motion.{name}")
        if node is None:
            continue
        wanted = (
            "cubic-bezier(" + ", ".join(_format_number(point) for point in points) + ")"
        )
        if str(current(node)) != wanted:
            node["value"] = wanted
            changes += 1

    numeric_pairs: list[tuple[str, str]] = []
    for token_path in source:
        match = re.match(r"^(spacing|radius|border)\.(.+)$", token_path)
        if match:
            numeric_pairs.append(
                (token_path, f"global.{match.group(1)}.{match.group(2)}")
            )
        match = re.match(r"^breakpoint\.(sm|md|lg|xl|xxl)$", token_path)
        if match:
            numeric_pairs.append((token_path, f"layout.breakpoint.{match.group(1)}"))
        match = re.match(r"^layout\.container-(max|prose|wide)$", token_path)
        if match:
            numeric_pairs.append((token_path, f"layout.container.{match.group(1)}"))
        # The source suffixes the responsive gutters (gutter-md) while Figma
        # nests them (gutter.md), because a Figma collection reads better as one
        # group with four members than as four siblings of the breakpoint set.
        match = re.match(r"^layout\.gutter(?:-(md|lg|xl))?$", token_path)
        if match:
            step = match.group(1) or "base"
            numeric_pairs.append((token_path, f"layout.gutter.{step}"))

    for source_path, figma_path in sorted(numeric_pairs):
        node = index.get(figma_path)
        if node is None:
            continue
        resolved = source.get(source_path)
        wanted = px_to_number(resolved)
        if wanted is None:
            if PERCENTAGE_SOURCES.get(source_path) == figma_path:
                continue
            outcome.failures.append(
                f"{source_path} resolves to {resolved!r}, which has no unitless "
                f"pixel equivalent for {figma_path}"
            )
            continue
        if str(current(node)) != wanted:
            node["value"] = wanted
            changes += 1

    verify_typography(source, tokens, index, outcome)

    if dry_run:
        outcome.written.append(
            f"{FIGMA_FILE}: {changes} value(s) would be rewritten (dry run)"
        )
        return
    if changes == 0:
        outcome.written.append(f"{FIGMA_FILE}: already in sync, not rewritten")
        return
    serialised = dump_studio(document) + "\n"
    path.write_text(serialised, encoding="utf-8")
    outcome.written.append(f"{FIGMA_FILE}: {changes} value(s) synced from tokens/")


def _format_number(value: Any) -> str:
    """Format a number the way a CSS cubic-bezier argument is written."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def verify_typography(
    source: Mapping[str, Any],
    tokens: Mapping[str, Json],
    index: Mapping[str, Any],
    outcome: Outcome,
) -> None:
    """Recompute the Figma type scale from source and fail on a disagreement."""
    roles = {
        path[len("typeScale.") :].split(".", 1)[1]: value
        for path, value in source.items()
        if path.startswith("typeScale.") and isinstance(value, Mapping)
    }
    checked = 0
    for role, composite in sorted(roles.items()):
        size = composite.get("fontSize")
        if not isinstance(size, str):
            continue
        match = re.fullmatch(r"([\d.]+)rem", size)
        if match is None:
            outcome.failures.append(
                f"typeScale role {role!r} has fontSize {size!r}, which is not a rem "
                "length and so cannot be converted to the pixel figure Figma needs"
            )
            continue
        size_px = float(match.group(1)) * ROOT_FONT_SIZE_PX
        node = index.get(f"typography.size.{role}")
        if node is not None and _numbers_differ(node.get("value"), size_px):
            outcome.failures.append(
                f"{FIGMA_FILE}:typography.size.{role} is {node.get('value')!r} but "
                f"{size} at a {ROOT_FONT_SIZE_PX}px root is {_trim(size_px)}"
            )
        elif node is not None:
            checked += 1

        line_height = composite.get("lineHeight")
        node = index.get(f"typography.line-height.{role}")
        if node is not None and isinstance(line_height, (int, float)):
            wanted = line_height * size_px
            if _numbers_differ(node.get("value"), wanted):
                outcome.failures.append(
                    f"{FIGMA_FILE}:typography.line-height.{role} is {node.get('value')!r} "
                    f"but {line_height} x {_trim(size_px)}px is {_trim(wanted)}"
                )
            else:
                checked += 1

        tracking = composite.get("letterSpacing")
        node = index.get(f"typography.letter-spacing.{role}")
        if node is not None and isinstance(tracking, str):
            em = re.fullmatch(r"(-?[\d.]+)em", tracking)
            if em is None:
                outcome.failures.append(
                    f"typeScale role {role!r} has letterSpacing {tracking!r}, which is "
                    "not an em length and so cannot be converted to pixels"
                )
                continue
            wanted = float(em.group(1)) * size_px
            if _numbers_differ(node.get("value"), wanted):
                outcome.failures.append(
                    f"{FIGMA_FILE}:typography.letter-spacing.{role} is {node.get('value')!r} "
                    f"but {tracking} at {_trim(size_px)}px is {_trim(wanted)}"
                )
            else:
                checked += 1

        weight = composite.get("fontWeight")
        node = index.get(f"typography.font-weight.{role}")
        if node is not None and isinstance(weight, (int, float)):
            wanted = FIGMA_WEIGHT_NAMES.get(int(weight))
            if wanted is None:
                outcome.failures.append(
                    f"typeScale role {role!r} uses weight {weight}, which has no Figma "
                    "style name in FIGMA_WEIGHT_NAMES"
                )
            elif node.get("value") != wanted:
                outcome.failures.append(
                    f"{FIGMA_FILE}:typography.font-weight.{role} is {node.get('value')!r} "
                    f"but weight {weight} is {wanted!r} in Figma"
                )
            else:
                checked += 1

    if checked:
        outcome.written.append(
            f"typography: {checked} converted value(s) verified against source"
        )


def _numbers_differ(declared: Any, wanted: float) -> bool:
    """Compare a Figma numeric string against a computed float, to 4 decimals."""
    if not isinstance(declared, (str, int, float)):
        return True
    try:
        return abs(float(declared) - wanted) > 5e-5
    except (TypeError, ValueError):
        return True


def _trim(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


# ---------------------------------------------------------------------------
# Font subsetting
# ---------------------------------------------------------------------------

#: Codepoints the self-hosted bundle must retain. Latin, Latin Extended-A for
#: Lithuanian, and the Cyrillic block plus the two characters that fall outside
#: it — U+0401 and U+0451, the letter Io, which Russian liturgical text uses
#: constantly and which a subsetter configured with "Cyrillic = U+0410-U+044F"
#: silently drops.
SUBSET_RANGES: tuple[tuple[int, int], ...] = (
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x00FF),  # Latin-1 Supplement
    (0x0100, 0x017F),  # Latin Extended-A: Lithuanian carons and ogoneks
    (0x0180, 0x024F),  # Latin Extended-B
    (0x02C6, 0x02DC),  # Spacing modifier letters
    (0x0300, 0x036F),  # Combining diacriticals
    (0x0400, 0x045F),  # Cyrillic, including Io at both ends
    (0x0490, 0x0491),  # Cyrillic Ghe with upturn
    (0x2000, 0x206F),  # General punctuation: the dashes and quotes prose needs
    (0x20A0, 0x20CF),  # Currency: the euro sign
    (0x2190, 0x21FF),  # Arrows
    (0x2200, 0x22FF),  # Mathematical operators
    (0x25A0, 0x25FF),  # Geometric shapes: the bullet
    (0xFB00, 0xFB06),  # Alphabetic presentation forms: the fi and fl ligatures
)

#: Fonts the bundle ships, as (family directory, source filename, weights).
FONT_SOURCES: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    ("fraunces", "Fraunces-Variable.ttf", (300, 400, 500, 600, 700)),
    ("inter", "Inter-Variable.ttf", (400, 500, 600, 700)),
)


def subset_codepoints() -> str:
    """Return the ``--unicodes`` argument fontTools expects."""
    return ",".join(f"U+{low:04X}-U+{high:04X}" for low, high in SUBSET_RANGES)


def build_fonts(repo_root: Path, outcome: Outcome, dry_run: bool) -> None:
    """Subset the variable fonts to the shipped weights and write WOFF2.

    Subsetting is a privacy measure as much as a performance one. A full Fraunces
    variable font is several hundred kilobytes covering every glyph the family
    supports; the subset covering Latin, Latin Extended and Cyrillic is a fraction
    of that, and a smaller file is also a file that finishes downloading before
    the reader has scrolled past the heading it renders.

    Two passes per weight, because ``pyftsubset`` has no instancer: a variable
    font is first pinned to the requested ``wght`` with
    ``fontTools.varLib.instancer`` and the resulting static font is then
    subsetted. Subsetting a variable font without pinning it keeps the whole
    ``gvar`` table, which is most of the file size and none of the benefit.

    UNEXERCISED IN THE REFERENCE ENVIRONMENT. fontTools is not installed where
    this was written, so the argument lists below are taken from the fontTools
    documentation and have not been run. ``--check`` does not cover this path.
    Run it once against a real font binary and confirm the output before
    relying on it in CI.
    """
    if not need(
        ftsubset, "fonttools", "pip install -r tools/requirements.txt", outcome
    ):
        return
    bundle = repo_root / "assets/typography/self-hosted-woff2"
    if not bundle.is_dir():
        outcome.failures.append(f"{bundle.relative_to(repo_root)} does not exist")
        return
    unicodes = subset_codepoints()
    for family, source_name, weights in FONT_SOURCES:
        source = bundle / source_name
        if not source.is_file():
            outcome.skipped.append(
                f"{source.relative_to(repo_root)} is not present; the licence permits "
                "redistribution but a several-hundred-kilobyte binary does not belong "
                "in a brand repository, so download it from the family's own release "
                "page and re-run --fonts"
            )
            continue
        for weight in weights:
            target = bundle / f"{family}-{weight}.woff2"
            if dry_run:
                outcome.written.append(f"{target.relative_to(repo_root)} (dry run)")
                continue
            pinned = source
            temporary: Path | None = None
            if weight != 400:
                temporary = bundle / f".{family}-{weight}.instanced.ttf"
                instanced = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "fontTools.varLib.instancer",
                        str(source),
                        f"wght={weight}",
                        "-o",
                        str(temporary),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if instanced.returncode != 0:
                    outcome.failures.append(
                        f"{source_name} at weight {weight}: instancing failed: "
                        f"{instanced.stderr.strip() or 'non-zero exit'}"
                    )
                    continue
                pinned = temporary
            subsetted = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "fontTools.subset",
                    str(pinned),
                    f"--unicodes={unicodes}",
                    "--flavor=woff2",
                    "--layout-features=kern,liga,clig,ccmp,locl,mark,mkmk,rlig,tnum,lnum",
                    "--name-IDs=1,2,3,4,6",
                    "--no-hinting",
                    "--desubroutinize",
                    f"--output-file={target}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if temporary is not None and temporary.is_file():
                temporary.unlink()
            if subsetted.returncode != 0:
                outcome.failures.append(
                    f"{source_name} at weight {weight}: subsetting failed: "
                    f"{subsetted.stderr.strip() or 'non-zero exit'}"
                )
                continue
            outcome.written.append(str(target.relative_to(repo_root)))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def summarise(outcomes: Sequence[Outcome], dry_run: bool) -> str:
    lines = ["build exports" + (" (dry run)" if dry_run else "")]
    for outcome in outcomes:
        lines.append(f"  {outcome.step}")
        for item in outcome.written:
            lines.append(f"    written   {item}")
        for item in outcome.skipped:
            lines.append(f"    skipped   {item}")
        for item in outcome.failures:
            lines.append(f"    FAILED    {item}")
    lines.append("")
    lines.append(
        f"{sum(len(o.written) for o in outcomes)} written, "
        f"{sum(len(o.skipped) for o in outcomes)} skipped, "
        f"{sum(len(o.failures) for o in outcomes)} failed"
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_exports.py",
        description="Build the distributable artefacts of the ViaVitae brand system.",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the SVG masters and the committed artefacts",
    )
    parser.add_argument(
        "--figma",
        action="store_true",
        help="sync build/figma-tokens/tokens.json from tokens/",
    )
    parser.add_argument(
        "--raster",
        action="store_true",
        help="rasterise the logo masters to PNG and WebP",
    )
    parser.add_argument(
        "--favicon", action="store_true", help="build the favicon and touch-icon set"
    )
    parser.add_argument(
        "--og", action="store_true", help="export the default Open Graph card"
    )
    parser.add_argument(
        "--social", action="store_true", help="export the social avatar"
    )
    parser.add_argument(
        "--fonts", action="store_true", help="subset the webfonts to WOFF2"
    )
    parser.add_argument("--all", action="store_true", help="every step above")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be written and write nothing",
    )
    arguments = parser.parse_args(argv)

    everything = arguments.all
    repo_root = arguments.repo_root.resolve()
    dry_run = arguments.dry_run
    outcomes: list[Outcome] = []

    def run(name: str, body: Callable[[Outcome], None]) -> None:
        outcome = Outcome(name)
        body(outcome)
        outcomes.append(outcome)

    def do_check(outcome: Outcome) -> None:
        check_svgs(repo_root, outcome)
        check_artefacts(repo_root, outcome)

    # Step name to implementation, in build order. --check runs first so a
    # malformed master is reported before anything is derived from it.
    #
    # Every command-line flag has exactly one entry here, and the "did the user
    # ask for anything" test below is derived from this table instead of being a
    # second disjunction written out above it. That ordering is the fix for a
    # defect this file actually had: --social appeared in the help text and in
    # the old disjunction but not in the dispatch, and the avatar was built by
    # the og step instead, so running `--social` on its own parsed cleanly,
    # selected nothing, wrote nothing and exited 0. A flag that silently does
    # nothing is worse than a flag that does not exist, because the person who
    # ran it believes the artefact was built.
    dispatch: list[tuple[str, bool, Callable[[Outcome], None]]] = [
        ("check", arguments.check or everything, do_check),
        (
            "figma",
            arguments.figma or everything,
            lambda o: sync_figma(repo_root, dry_run, o),
        ),
        (
            "raster",
            arguments.raster or everything,
            lambda o: build_raster(repo_root, o, dry_run),
        ),
        (
            "favicon",
            arguments.favicon or everything,
            lambda o: build_favicon(repo_root, o, dry_run),
        ),
        ("og", arguments.og or everything, lambda o: build_og(repo_root, o, dry_run)),
        (
            "social",
            arguments.social or everything,
            lambda o: build_social(repo_root, o, dry_run),
        ),
        (
            "fonts",
            arguments.fonts or everything,
            lambda o: build_fonts(repo_root, o, dry_run),
        ),
    ]

    if not any(selected for _, selected, _ in dispatch):
        parser.print_help()
        return 2

    for name, selected, body in dispatch:
        if selected:
            run(name, body)

    print(summarise(outcomes, dry_run))

    if any(not outcome.ok for outcome in outcomes):
        return 1
    # A step that produced nothing and skipped everything could not run: the
    # dependency or the source file is missing. That is a distinct condition from
    # a failed build and CI treats it differently, so it gets its own exit code.
    if any(
        outcome.skipped and not outcome.written and not outcome.failures
        for outcome in outcomes
    ):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
