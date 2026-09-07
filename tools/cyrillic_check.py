#!/usr/bin/env python3
"""Verify that the fonts this brand ships can actually set the languages it claims.

A font coverage gap is the worst class of typography defect, because it is
invisible to everybody who would catch it in review. Fraunces does not declare
Cyrillic coverage. A Russian heading set in Fraunces therefore falls back glyph
by glyph: some letters render in Fraunces, the rest in whatever serif the browser
chooses, and the result is one line of text in two typefaces at two different
x-heights. An English-speaking reviewer sees a heading. A Russian reader sees a
mistake. Nothing in the build fails, nothing in the diff looks wrong, and the
only way to find it is to know to look.

This script runs two audits, deliberately separated because they have different
dependencies and different failure semantics.

**Declaration audit** (no dependencies, always runs, this is the CI gate)
    Every locale marked ``supported`` in ``tokens/typography.json`` must declare
    the codepoints it needs, in a valid format, and the declared set must be
    complete for the language — a list that quietly omits U+0401 is worse than
    no list, because it has been checked and passed. Completeness is tested
    against a reference alphabet derived from the Unicode block structure rather
    than from a hand-typed list, so the check does not inherit the same typo it
    is meant to catch.

**Binary audit** (needs fontTools and font files; ``--fonts``)
    Reads the ``cmap`` of each font binary and reports, per locale and per
    weight, which required codepoints are actually present. Also reads ``fvar``
    to confirm a variable font's ``wght`` axis reaches every weight the token set
    declares, because a weight outside the axis range silently rounds to the
    nearest available instance and the design is then not what ships.

The binary audit exits **2**, not 0, when it cannot run. Font binaries are not
committed to this repository — a several-hundred-kilobyte variable font does not
belong in a brand repo, and the download step is a contributor action. A check
that reported success because it found nothing to check would be a gate that
opens every time, so CI runs the declaration audit on every pull request and the
binary audit in the release job, where the fonts have been fetched.

Usage
-----
    python3 tools/cyrillic_check.py                  # declaration audit
    python3 tools/cyrillic_check.py --fonts          # plus the binary audit
    python3 tools/cyrillic_check.py --fonts --font-dir path/to/fonts
    python3 tools/cyrillic_check.py --verbose
    python3 tools/cyrillic_check.py --locale ru      # one locale

Exit codes
----------
    0  the declaration audit passed, and the binary audit passed if it ran
    1  a declared requirement is wrong, incomplete, or a binary is missing glyphs
    2  the binary audit was requested and could not run: fontTools absent or no
       font binaries found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Bare `# type: ignore`, no error code, and deliberately so: fontTools is absent
# on a machine that has not installed it (`import-not-found`) and present but
# untyped on one that has (`import-untyped`). Naming either code makes the ignore
# wrong in the other environment, and `--strict` reports a wrong code as an
# unused ignore. A bare ignore is correct in both. See the same note in
# tools/build_exports.py.
try:  # pragma: no cover - exercised only where fontTools is installed
    from fontTools.ttLib import TTFont  # type: ignore
except ImportError:  # pragma: no cover
    TTFont = None

TYPOGRAPHY_FILE = "tokens/typography.json"

#: Where font binaries are looked for, in order, when ``--font-dir`` is absent.
DEFAULT_FONT_DIRS: tuple[str, ...] = (
    "assets/typography/self-hosted-woff2",
    "assets/typography/fraunces",
    "assets/typography/inter",
)

FONT_SUFFIXES = frozenset({".ttf", ".otf", ".woff", ".woff2"})

#: A codepoint as the token set writes it.
CODEPOINT_RE = re.compile(r"^U\+([0-9A-Fa-f]{4,6})$")

#: Locales whose coverage is asserted here. A locale the token set marks
#: ``stubbed`` is reported as skipped rather than checked, and a locale marked
#: ``supported`` without a reference here is a failure: it means somebody added a
#: language and did not add the audit for it.
SUPPORTED_STATUS = "supported"
STUBBED_STATUS = "stubbed"


def _cyrillic_reference() -> frozenset[int]:
    """The 66 codepoints of the modern Russian alphabet, both cases.

    Derived from the block structure rather than typed out: the Cyrillic block
    runs U+0410-U+042F uppercase and U+0430-U+044F lowercase, which is 32
    letters each, and the letter Io sits outside both ranges at U+0401 and
    U+0451. That is 33 letters and 66 codepoints. Io is the one that gets
    dropped, because a range-based subset configured as "U+0410-U+044F" looks
    complete and is not.
    """
    upper = set(range(0x0410, 0x0430)) | {0x0401}
    lower = set(range(0x0430, 0x0450)) | {0x0451}
    return frozenset(upper | lower)


def _lithuanian_reference() -> frozenset[int]:
    """The 18 codepoints Lithuanian adds to the Latin alphabet.

    Nine letters — a ogonek, c caron, e dot, e ogonek, i ogonek, s caron,
    u macron, u ogonek, z caron — in both cases. These are the accented letters
    of the standard Lithuanian alphabet and not a subset of Latin Extended-A
    chosen for convenience: omitting one means a common word cannot be set.
    """
    upper = (0x0104, 0x010C, 0x0116, 0x0118, 0x012E, 0x0160, 0x016A, 0x0172, 0x017D)
    return frozenset(upper) | frozenset(point + 1 for point in upper)


def _english_reference() -> frozenset[int]:
    """The typographic characters English prose requires beyond Basic Latin.

    Curly quotes, the apostrophe, en and em dash, ellipsis and the non-breaking
    space. A face missing these is not unusable for English, but content that
    uses them will fall back per character, and the fallback is a different
    typeface in the middle of a sentence.
    """
    return frozenset({0x2018, 0x2019, 0x201C, 0x201D, 0x2013, 0x2014, 0x2026, 0x00A0})


#: Locale code to the codepoints its declaration must at minimum cover.
REFERENCE_ALPHABETS: dict[str, frozenset[int]] = {
    "lt": _lithuanian_reference(),
    "en": _english_reference(),
    "ru": _cyrillic_reference(),
}


@dataclass(frozen=True)
class Finding:
    """One problem, with the locale and file it belongs to."""

    kind: str
    location: str
    message: str

    def render(self) -> str:
        return f"[{self.kind}] {self.location}\n    {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def fail(self, kind: str, location: str, message: str) -> None:
        finding = Finding(kind, location, message)
        if finding not in self.findings:
            self.findings.append(finding)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def count(self, key: str, amount: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + amount

    @property
    def ok(self) -> bool:
        return not self.findings


def describe(codepoints: Iterable[int]) -> str:
    """Render codepoints as ``U+0401 (Ё)``, which is readable by a non-specialist.

    A coverage report that lists ``0x401`` is a report only its author can act
    on. The character next to the number is what lets a designer confirm the gap
    is real without opening a character map.
    """
    items = sorted(codepoints)
    if not items:
        return "none"
    shown = ", ".join(f"U+{point:04X} ({chr(point)})" for point in items[:12])
    if len(items) > 12:
        return f"{shown} and {len(items) - 12} more"
    return shown


def parse_codepoints(raw: Any, location: str, report: Report) -> set[int]:
    """Parse a ``requiredCodepoints`` list, reporting every malformed entry."""
    if not isinstance(raw, list) or not raw:
        report.fail(
            "declaration",
            location,
            "requiredCodepoints must be a non-empty array of U+XXXX strings",
        )
        return set()
    parsed: set[int] = set()
    for entry in raw:
        if not isinstance(entry, str):
            report.fail("declaration", location, f"{entry!r} is not a string")
            continue
        match = CODEPOINT_RE.match(entry.strip())
        if match is None:
            report.fail(
                "declaration",
                location,
                f"{entry!r} is not U+XXXX; a codepoint written any other way is "
                "one a reviewer cannot look up",
            )
            continue
        point = int(match.group(1), 16)
        if point > 0x10FFFF:
            report.fail(
                "declaration", location, f"{entry} is outside the Unicode range"
            )
            continue
        if not entry.isupper() or entry != entry.strip():
            report.fail(
                "declaration",
                location,
                f"{entry!r} is not in the canonical form U+0401 with uppercase hex digits",
            )
        parsed.add(point)
    return parsed


def check_declarations(
    locales: Mapping[str, Any], report: Report, only: Sequence[str] | None
) -> dict[str, set[int]]:
    """Audit what the token set declares, without reading a single font."""
    requirements: dict[str, set[int]] = {}
    supported: list[str] = []
    for code, entry in locales.items():
        if code.startswith("$"):
            continue
        if only and code not in only:
            continue
        location = f"{TYPOGRAPHY_FILE}:locale.{code}"
        if not isinstance(entry, Mapping):
            report.fail("declaration", location, "a locale entry must be an object")
            continue
        status = entry.get("status")
        if status == STUBBED_STATUS:
            report.note(
                f"{code} ({entry.get('displayName', code)}) is stubbed; not audited"
            )
            continue
        if status != SUPPORTED_STATUS:
            report.fail(
                "declaration",
                location,
                f"status is {status!r}; expected {SUPPORTED_STATUS!r} or {STUBBED_STATUS!r}",
            )
            continue
        supported.append(code)

        declared = parse_codepoints(entry.get("requiredCodepoints"), location, report)
        requirements[code] = declared
        reference = REFERENCE_ALPHABETS.get(code)
        if reference is None:
            report.fail(
                "declaration",
                location,
                f"{code} is marked supported but has no entry in REFERENCE_ALPHABETS, "
                "so its declaration is not checked for completeness; add the "
                "reference alphabet for the language before shipping it",
            )
        else:
            missing = reference - declared
            if missing:
                report.fail(
                    "declaration",
                    location,
                    f"declared codepoints are incomplete for {entry.get('displayName', code)}: "
                    f"missing {describe(missing)}. A truncated list that passes is "
                    "worse than no list, because it has been checked",
                )
            extra = declared - reference
            if extra:
                report.note(
                    f"{code} declares {len(extra)} codepoint(s) beyond the reference "
                    f"alphabet: {describe(extra)}"
                )
            if not missing:
                report.count("declarations")

        display = entry.get("fontFamilyDisplay")
        ui = entry.get("fontFamilyUi")
        if not isinstance(display, str) or not display.startswith("{"):
            report.fail(
                "declaration",
                location,
                f"fontFamilyDisplay is {display!r}, not an alias",
            )
        if not isinstance(ui, str) or not ui.startswith("{"):
            report.fail(
                "declaration", location, f"fontFamilyUi is {ui!r}, not an alias"
            )
        if display != "{fontFamily.display}" and not isinstance(
            entry.get("$description"), str
        ):
            report.fail(
                "declaration",
                location,
                f"the display family is {display}, not the default, and no "
                "$description explains why; a substituted display face is a "
                "visible identity decision and has to be on the record",
            )
        if not isinstance(entry.get("notes"), str) or not entry["notes"].strip():
            report.fail(
                "declaration",
                location,
                "no notes field; a supported locale records how its diacritics "
                "interact with line-height and case transforms",
            )
    if not supported:
        report.fail(
            "declaration",
            TYPOGRAPHY_FILE,
            "no locale is marked supported, so there is nothing for this audit to cover",
        )
    return requirements


def find_fonts(repo_root: Path, font_dir: str | None, report: Report) -> list[Path]:
    """Locate font binaries to audit."""
    if font_dir is not None:
        candidates = [Path(font_dir)]
    else:
        candidates = [repo_root / relative for relative in DEFAULT_FONT_DIRS]
    found: list[Path] = []
    for directory in candidates:
        if not directory.is_dir():
            continue
        found.extend(
            sorted(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in FONT_SUFFIXES
            )
        )
    return found


def font_codepoints(path: Path) -> set[int]:
    """Every codepoint a font maps to a glyph, across all of its cmap subtables.

    All subtables, not the first: a WOFF2 built for the web often carries a
    format-12 subtable for the supplementary planes alongside a format-4 one for
    the BMP, and reading only the first misses whichever block is in the second.
    """
    font = TTFont(str(path), lazy=True, fontNumber=0)
    try:
        covered: set[int] = set()
        for table in font["cmap"].tables:
            covered.update(table.cmap.keys())
        return covered
    finally:
        font.close()


def font_weight_axis(path: Path) -> tuple[float, float] | None:
    """The ``wght`` axis range of a variable font, or None for a static font."""
    font = TTFont(str(path), lazy=True, fontNumber=0)
    try:
        if "fvar" not in font:
            return None
        for axis in font["fvar"].axes:
            if axis.axisTag == "wght":
                return (axis.minValue, axis.maxValue)
        return None
    finally:
        font.close()


def static_weight(path: Path) -> int | None:
    """The weight a static font declares, from its head.macStyle and OS/2 tables."""
    font = TTFont(str(path), lazy=True, fontNumber=0)
    try:
        os2 = font.get("OS/2")
        if os2 is not None and getattr(os2, "usWeightClass", None):
            return int(os2.usWeightClass)
        return None
    finally:
        font.close()


def check_binaries(
    repo_root: Path,
    requirements: Mapping[str, set[int]],
    weights: Sequence[int],
    font_dir: str | None,
    report: Report,
) -> int:
    """Audit the actual font binaries. Returns the exit code contribution."""
    if TTFont is None:
        report.fail(
            "dependency",
            "tools/requirements.txt",
            "fontTools is not installed, so no cmap could be read. Run: "
            "pip install -r tools/requirements.txt. This is reported as a failure "
            "rather than a pass because a coverage check that read nothing has "
            "verified nothing",
        )
        return 2

    fonts = find_fonts(repo_root, font_dir, report)
    if not fonts:
        searched = font_dir or ", ".join(DEFAULT_FONT_DIRS)
        report.fail(
            "fonts",
            searched,
            "no .ttf, .otf, .woff or .woff2 files found. Font binaries are not "
            "committed to this repository; fetch Fraunces and Inter from their own "
            "release pages into assets/typography/self-hosted-woff2 and re-run, or "
            "point --font-dir at a directory that holds them",
        )
        return 2

    for path in fonts:
        relative = path.name
        try:
            covered = font_codepoints(path)
        except Exception as exc:  # noqa: BLE001 - fontTools raises many types
            report.fail("binary", relative, f"could not be read: {exc}")
            continue
        report.count("binaries")

        axis = font_weight_axis(path)
        if axis is None:
            declared = static_weight(path)
            if declared is None:
                report.fail(
                    "binary", relative, "is static but declares no usWeightClass"
                )
            elif declared not in weights:
                report.fail(
                    "binary",
                    relative,
                    f"is a static face at weight {declared}, which tokens/typography.json "
                    f"does not list; the permitted weights are {', '.join(str(w) for w in weights)}",
                )
            else:
                report.count("weights")
        else:
            low, high = axis
            outside = [weight for weight in weights if not low <= weight <= high]
            if outside:
                report.fail(
                    "binary",
                    relative,
                    f"has a wght axis of {low:g}-{high:g}, which does not reach "
                    f"{', '.join(str(w) for w in outside)}. A weight outside the "
                    "axis range silently rounds to the nearest instance, so the "
                    "design is not what ships",
                )
            else:
                report.count("weights", len(weights))

        for code, required in sorted(requirements.items()):
            missing = required - covered
            if missing:
                report.fail(
                    "coverage",
                    f"{relative}:{code}",
                    f"is missing {len(missing)} required codepoint(s): {describe(missing)}. "
                    "Text needing one of these falls back per glyph, so a single "
                    "line renders in two typefaces",
                )
            else:
                report.count("coverage")
    return 0


COUNT_LABELS: tuple[tuple[str, str], ...] = (
    ("declarations", "locale declarations complete"),
    ("binaries", "font binaries read"),
    ("weights", "weight checks passed"),
    ("coverage", "locale/binary coverage checks passed"),
)


def format_report(report: Report, verbose: bool, binary_ran: bool) -> str:
    lines = ["font coverage"]
    for key, label in COUNT_LABELS:
        if key in report.counts:
            lines.append(f"  {label:<40} {report.counts[key]}")
    lines.append(
        f"  {'binary audit run' if binary_ran else 'binary audit NOT run (declaration audit only)'}"
    )
    if report.findings:
        lines.append("")
        lines.append(f"findings ({len(report.findings)})")
        for finding in report.findings:
            lines.append("  " + finding.render().replace("\n", "\n  "))
    elif not verbose:
        lines.append(
            "Every declared requirement is complete"
            + (" and covered." if binary_ran else ".")
        )
    if verbose and report.notes:
        lines.append("")
        lines.append("notes")
        for note in report.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def run(
    repo_root: Path,
    check_fonts: bool,
    font_dir: str | None,
    only: Sequence[str] | None,
    verbose: bool,
    as_json: bool,
) -> int:
    report = Report()
    path = repo_root / TYPOGRAPHY_FILE
    if not path.is_file():
        report.fail("declaration", TYPOGRAPHY_FILE, "file is missing")
        print(format_report(report, verbose, False))
        return 1
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.fail("declaration", TYPOGRAPHY_FILE, f"not valid JSON: {exc}")
        print(format_report(report, verbose, False))
        return 1

    locales = document.get("locale")
    if not isinstance(locales, Mapping):
        report.fail("declaration", TYPOGRAPHY_FILE, "no locale group")
        print(format_report(report, verbose, False))
        return 1

    requirements = check_declarations(locales, report, only)

    weights: list[int] = []
    for name, token in sorted(document.get("fontWeight", {}).items()):
        if name.startswith("$") or not isinstance(token, Mapping):
            continue
        value = token.get("$value")
        if isinstance(value, int):
            weights.append(value)
    if not weights:
        report.fail(
            "declaration",
            f"{TYPOGRAPHY_FILE}:fontWeight",
            "no numeric weights declared, so there is nothing for the binary audit to check",
        )

    binary_code = 0
    if check_fonts:
        binary_code = check_binaries(repo_root, requirements, weights, font_dir, report)

    if as_json:
        print(
            json.dumps(
                {
                    "ok": report.ok,
                    "binaryAuditRan": check_fonts and binary_code == 0,
                    "counts": report.counts,
                    "findings": [
                        {"kind": f.kind, "location": f.location, "message": f.message}
                        for f in report.findings
                    ],
                    "notes": report.notes if verbose else [],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(format_report(report, verbose, check_fonts and binary_code == 0))

    if not report.ok:
        return binary_code or 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cyrillic_check.py",
        description=(
            "Verify that the fonts this brand ships can set every locale it claims "
            "to support, and that the declared codepoint lists are complete."
        ),
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument(
        "--fonts",
        action="store_true",
        help="also read the font binaries and check their cmap and wght axis",
    )
    parser.add_argument("--font-dir", help="directory holding the font binaries")
    parser.add_argument(
        "--locale",
        action="append",
        dest="locales",
        help="restrict to a locale code; repeatable",
    )
    parser.add_argument("--verbose", action="store_true", help="include the notes")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    arguments = parser.parse_args(argv)
    return run(
        arguments.repo_root.resolve(),
        arguments.fonts,
        arguments.font_dir,
        arguments.locales,
        arguments.verbose,
        arguments.as_json,
    )


if __name__ == "__main__":
    sys.exit(main())
