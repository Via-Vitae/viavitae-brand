#!/usr/bin/env python3
"""Verify every declared colour pair in the ViaVitae token set against WCAG 2.x.

This is the gate that keeps the colour system honest. A contrast ratio is not a
matter of taste and not something a reviewer can eyeball: gold at #C9A227 on
ivory at #F7F4EC looks like a perfectly good brand pairing and measures 2.20:1,
which fails AA, AA-large and the 3:1 non-text threshold all at once. Every
text/background pair the system ships is declared in the ``$extensions`` block of
``tokens/colors.json`` and ``tokens/colors.church.json``; this script resolves
each declaration to a literal colour, computes the ratio from the WCAG
definition, and fails the build when a pair falls below its declared minimum.

It also fails when the contract is incomplete. A semantic ``text`` role that no
declared pair covers is an unverified colour, and "nobody wrote it down" is
indistinguishable from "nobody checked it". The same applies in reverse to the
``prohibited`` list: an entry there asserts that a combination still fails, so if
a palette change makes one pass, the entry is stale guidance and is reported
rather than silently continuing to tell designers not to do something that is now
fine.

Usage
-----
    python3 tools/contrast_check.py                 # human-readable report
    python3 tools/contrast_check.py --json          # machine-readable result
    python3 tools/contrast_check.py --verbose       # include passing pairs
    python3 tools/contrast_check.py --repo-root ..  # run from another directory

Exit codes
----------
    0  every declared pair passes and the contract is complete
    1  at least one pair fails, or the contract is incomplete, or an entry in the
       prohibited list is stale
    2  the token files could not be read or parsed

No third-party dependencies. The arithmetic is the WCAG definition and is written
out in full below; taking a dependency for twenty lines of standard-library maths
would add supply-chain surface to the one gate whose whole purpose is to be
trustworthy.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Token files that may declare colour tokens and contrast contracts. Both are
#: merged into one namespace, because ``colors.church.json`` aliases into
#: ``colors.json`` (for example ``{color.palette.gold.500}``).
TOKEN_FILES: tuple[str, ...] = ("tokens/colors.json", "tokens/colors.church.json")

#: Key holding the contrast contract inside each token file's ``$extensions``.
CONTRACT_KEY = "com.viavitae.contrast-pairs"

#: Sections of the contract that list ``{foreground, background, minimum}`` pairs.
PAIR_SECTIONS: tuple[str, ...] = (
    "text-on-surface",
    "non-text-on-surface",
    "chart-series-on-surface",
)

#: Section listing chart ramps whose consecutive entries must stay separable.
SEPARATION_SECTION = "chart-series-separation"

#: Section listing combinations asserted to still fail.
PROHIBITED_SECTION = "prohibited"

#: An alias reference, ``{dotted.path}``.
ALIAS_RE = re.compile(r"^\{([A-Za-z0-9_.\-]+)\}$")

#: A 6- or 8-digit hex colour, with or without the leading ``#``.
HEX_RE = re.compile(r"^#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")

#: Keys that are never token groups or tokens.
RESERVED_KEYS = frozenset({"$description", "$extensions", "$value", "$type", "meta"})

#: Rounding used when reporting a ratio. Two decimals is what the WCAG conformance
#: language uses and is enough resolution to distinguish 4.48 from 4.52, which is
#: the difference between a pass and a fail at the AA threshold.
RATIO_PRECISION = 2

#: Slack tolerated when asserting that a prohibited pair still fails. A ratio is
#: reported to two decimals but computed in float, so an exact comparison against
#: the documented figure would flap on the last digit.
PROHIBITED_TOLERANCE = 0.02


Json = Mapping[str, Any]


# ---------------------------------------------------------------------------
# WCAG 2.x colour arithmetic
# ---------------------------------------------------------------------------


def _linearise(channel: int) -> float:
    """Apply the sRGB inverse companding to one 8-bit channel.

    WCAG 2.x specifies a threshold of 0.03928 on the normalised value. The
    mathematically correct sRGB threshold is 0.04045; the two differ only for
    channel values 10 and 11, where the resulting luminance difference is far
    below anything a contrast decision turns on. The specified value is used
    because conformance is measured against the specification, not against the
    standard it approximates.
    """
    normalised = channel / 255.0
    if normalised <= 0.03928:
        return normalised / 12.92
    # Bound to a float-annotated name rather than returned directly: `float **
    # float` comes back as Any from mypy's point of view, and a function declared
    # `-> float` that returns Any is the one place `--strict` cannot follow the
    # arithmetic into the caller. Everything downstream of this function is
    # contrast decisions, so the return type is worth pinning explicitly.
    companded: float = ((normalised + 0.055) / 1.055) ** 2.4
    return companded


def relative_luminance(red: int, green: int, blue: int) -> float:
    """WCAG 2.x relative luminance of an opaque sRGB colour, in [0, 1].

    The coefficients are those in the specification: 0.2126 red, 0.7152 green,
    0.0722 blue.
    """
    return (
        0.2126 * _linearise(red)
        + 0.7152 * _linearise(green)
        + 0.0722 * _linearise(blue)
    )


@dataclass(frozen=True)
class Rgba:
    """An sRGB colour with an alpha channel, each component 0-255."""

    red: int
    green: int
    blue: int
    alpha: int = 255

    @property
    def is_translucent(self) -> bool:
        return self.alpha < 255


def parse_hex(value: str) -> Rgba:
    """Parse ``#RRGGBB`` or ``#RRGGBBAA`` into components.

    Raises ``ValueError`` with the offending text in the message, because a
    malformed colour in a token file must be reported as a defect in that file
    rather than surfacing later as an arithmetic error.
    """
    match = HEX_RE.match(value.strip())
    if match is None:
        raise ValueError(f"not a 6- or 8-digit hex colour: {value!r}")
    digits = match.group(1)
    red = int(digits[0:2], 16)
    green = int(digits[2:4], 16)
    blue = int(digits[4:6], 16)
    alpha = int(digits[6:8], 16) if len(digits) == 8 else 255
    return Rgba(red, green, blue, alpha)


def composite(foreground: Rgba, background: Rgba) -> Rgba:
    """Alpha-composite ``foreground`` over ``background``, both opaque in result.

    A contrast ratio is undefined for a translucent colour in isolation: the ratio
    depends on whatever is behind it. The overlay and scrim tokens are
    translucent, so they are composited over the background they are paired with
    before the ratio is taken. Compositing is done in gamma-encoded sRGB space,
    which is what every browser does, rather than in linear space, which would be
    more physically accurate and would disagree with the rendering it is meant to
    describe.
    """
    alpha = foreground.alpha / 255.0
    red = round(foreground.red * alpha + background.red * (1.0 - alpha))
    green = round(foreground.green * alpha + background.green * (1.0 - alpha))
    blue = round(foreground.blue * alpha + background.blue * (1.0 - alpha))
    return Rgba(red, green, blue, 255)


def contrast_ratio(first: Rgba, second: Rgba) -> float:
    """WCAG 2.x contrast ratio, in [1, 21]. Symmetric: order does not matter.

    Translucent inputs are an error here rather than being silently treated as
    opaque, because the caller must say what they sit on. Use :func:`composite`
    first.
    """
    if first.is_translucent or second.is_translucent:
        raise ValueError(
            "contrast_ratio requires opaque colours; composite the translucent "
            "colour over its background first"
        )
    luminance_a = relative_luminance(first.red, first.green, first.blue)
    luminance_b = relative_luminance(second.red, second.green, second.blue)
    lighter = max(luminance_a, luminance_b)
    darker = min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def resolve_pair(foreground: str, background: str) -> float:
    """Contrast ratio between two hex strings, compositing alpha where present."""
    back = parse_hex(background)
    front = parse_hex(foreground)
    if front.is_translucent:
        front = composite(front, back)
    if back.is_translucent:
        # A translucent background over an unknown page cannot be resolved. The
        # token set does not use one as a background, so this is a defect report
        # rather than a case to handle.
        raise ValueError(
            f"background {background!r} is translucent; a contrast ratio against "
            "it depends on the page beneath it"
        )
    return contrast_ratio(front, back)


# ---------------------------------------------------------------------------
# Token loading and alias resolution
# ---------------------------------------------------------------------------


class TokenError(Exception):
    """Raised when the token set is malformed rather than merely failing a check."""


def load_token_files(repo_root: Path) -> Json:
    """Load and shallow-merge the colour token files into one namespace.

    ``colors.church.json`` aliases into ``colors.json``, so both must be present
    in one namespace for resolution to work. A top-level key collision is an
    error rather than a silent overwrite: two files claiming the same root means
    one of them is wrong about what it owns.
    """
    merged: dict[str, Any] = {}
    for relative in TOKEN_FILES:
        path = repo_root / relative
        if not path.is_file():
            raise TokenError(f"missing token file: {relative}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TokenError(f"{relative} is not valid JSON: {exc}") from exc
        if not isinstance(document, dict):
            raise TokenError(f"{relative} must contain a JSON object at its root")
        for key, value in document.items():
            if key in RESERVED_KEYS:
                continue
            if key in merged:
                raise TokenError(
                    f"top-level key {key!r} is declared in more than one of "
                    f"{', '.join(TOKEN_FILES)}"
                )
            merged[key] = value
    return merged


def walk_tokens(node: Any, prefix: str) -> dict[str, Any]:
    """Flatten a DTCG tree into ``{dotted.path: token}``.

    A node is a token when it carries ``$value``; otherwise it is a group and is
    descended into. Keys beginning with ``$`` other than the two that define a
    token are annotations and are skipped, so a ``$description`` on a group does
    not become a child token.
    """
    found: dict[str, Any] = {}
    if not isinstance(node, Mapping):
        return found
    if "$value" in node:
        found[prefix] = node
        return found
    for key, value in node.items():
        if key.startswith("$"):
            continue
        child_prefix = f"{prefix}.{key}" if prefix else str(key)
        found.update(walk_tokens(value, child_prefix))
    return found


def resolve_alias(tokens: Mapping[str, Any], reference: str) -> str:
    """Follow ``{dotted.path}`` references to a literal colour string.

    Detects cycles, because an alias loop in a token file otherwise presents as a
    ``RecursionError`` deep inside the resolver with no indication of which two
    tokens are responsible. The visited path is included in the message for
    exactly that reason.
    """
    seen: list[str] = []
    current = reference
    while True:
        match = ALIAS_RE.match(current.strip()) if isinstance(current, str) else None
        if match is None:
            if not isinstance(current, str):
                raise TokenError(
                    f"alias chain from {reference!r} resolved to a non-string: "
                    f"{current!r}"
                )
            return current
        path = match.group(1)
        if path in seen:
            chain = " -> ".join([*seen, path])
            raise TokenError(f"circular alias: {chain}")
        seen.append(path)
        token = tokens.get(path)
        if token is None:
            chain = " -> ".join(seen)
            raise TokenError(f"unresolved alias: {chain} (no token at {path!r})")
        current = token.get("$value")
        if current is None:
            raise TokenError(f"token at {path!r} has no $value")


def resolve_colour(tokens: Mapping[str, Any], reference: str) -> tuple[str, str]:
    """Resolve a colour reference to ``(hex, resolved_path)``.

    The resolved path is returned alongside the literal so that a failure message
    can name the token a designer will recognise rather than only the alias the
    contract happened to use.
    """
    match = ALIAS_RE.match(reference.strip())
    if match is None:
        # A literal hex value written straight into the contract. Permitted, so
        # that a one-off verification (a third-party colour, a print ink) does not
        # require inventing a token for it.
        return reference, reference
    path = match.group(1)
    if path not in tokens:
        raise TokenError(f"contract references {path!r}, which is not a token")
    literal = resolve_alias(tokens, reference)
    return literal, path


def load_contracts(repo_root: Path) -> tuple[Json, list[Json]]:
    """Return the flattened token map and every contrast contract found."""
    merged = load_token_files(repo_root)
    tokens = walk_tokens(merged, "")
    extensions = merged.get("$extensions")
    contracts: list[Json] = []
    if isinstance(extensions, Mapping):
        contract = extensions.get(CONTRACT_KEY)
        if isinstance(contract, Mapping):
            contracts.append(contract)

    # ``colors.church.json`` keeps its own contract under its own ``$extensions``,
    # so each file is re-read for that key rather than relying on the merge, which
    # would have raised on the duplicate ``$extensions``.
    for relative in TOKEN_FILES:
        document = json.loads((repo_root / relative).read_text(encoding="utf-8"))
        file_extensions = document.get("$extensions")
        if not isinstance(file_extensions, Mapping):
            continue
        file_contract = file_extensions.get(CONTRACT_KEY)
        if isinstance(file_contract, Mapping) and file_contract not in contracts:
            contracts.append(file_contract)

    if not contracts:
        raise TokenError(
            f"no contrast contract found under $extensions[{CONTRACT_KEY!r}] in "
            f"{', '.join(TOKEN_FILES)}"
        )
    return tokens, contracts


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairResult:
    """The outcome of one foreground/background check."""

    section: str
    foreground_ref: str
    background_ref: str
    foreground_hex: str
    background_hex: str
    ratio: float
    required: float
    sc: str
    note: str
    passed: bool

    @property
    def label(self) -> str:
        return f"{self.foreground_ref} on {self.background_ref}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "label": self.label,
            "foreground": self.foreground_hex,
            "background": self.background_hex,
            "ratio": round(self.ratio, RATIO_PRECISION),
            "required": self.required,
            "sc": self.sc,
            "note": self.note,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class CoverageResult:
    """A token that should have been covered by a declared pair but was not."""

    token_path: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"token": self.token_path, "reason": self.reason}


@dataclass(frozen=True)
class StaleResult:
    """A prohibited entry whose combination no longer fails."""

    foreground_ref: str
    background_ref: str
    ratio: float
    asserted_maximum: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "foreground": self.foreground_ref,
            "background": self.background_ref,
            "ratio": round(self.ratio, RATIO_PRECISION),
            "asserted_maximum": self.asserted_maximum,
            "reason": self.reason,
        }


def check_pairs(
    tokens: Mapping[str, Any], contract: Json, section: str
) -> list[PairResult]:
    """Check every ``{foreground, background, minimum}`` entry in one section."""
    entries = contract.get(section)
    if not isinstance(entries, Sequence):
        return []
    results: list[PairResult] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise TokenError(f"{section}[{index}] is not an object")
        for required_key in ("foreground", "background", "minimum"):
            if required_key not in entry:
                raise TokenError(f"{section}[{index}] is missing {required_key!r}")
        foreground_ref = str(entry["foreground"])
        background_ref = str(entry["background"])
        minimum = float(entry["minimum"])
        sc = str(entry.get("sc", ""))
        note = str(entry.get("note", ""))
        foreground_hex, foreground_path = resolve_colour(tokens, foreground_ref)
        background_hex, background_path = resolve_colour(tokens, background_ref)
        ratio = resolve_pair(foreground_hex, background_hex)
        results.append(
            PairResult(
                section=section,
                foreground_ref=foreground_path,
                background_ref=background_path,
                foreground_hex=foreground_hex,
                background_hex=background_hex,
                ratio=ratio,
                required=minimum,
                sc=sc,
                note=note,
                passed=ratio >= minimum,
            )
        )
    return results


def check_separation(
    tokens: Mapping[str, Any], contract: Json
) -> tuple[list[PairResult], list[str]]:
    """Check that consecutive entries in each chart ramp stay separable.

    Returns pair results for the consecutive comparisons plus a list of hard
    errors for a malformed ramp. Consecutive pairs only: the property that
    matters is that two series sitting next to each other in a legend or a
    stacked bar can be told apart. Non-adjacent pairs in a hue-separated ramp are
    naturally close in luminance and requiring them all to separate would force a
    palette that is not a palette.
    """
    block = contract.get(SEPARATION_SECTION)
    errors: list[str] = []
    results: list[PairResult] = []
    if not isinstance(block, Mapping):
        return results, errors
    for ramp_name, ramp in block.items():
        if ramp_name.startswith("$") or not isinstance(ramp, Mapping):
            continue
        references = ramp.get("ramp")
        if not isinstance(references, Sequence) or len(references) < 2:
            errors.append(
                f"{SEPARATION_SECTION}.{ramp_name}.ramp must be a list of at "
                "least two colour references"
            )
            continue
        minimum = float(ramp.get("minimum", 1.3))
        hexes: list[str] = []
        paths: list[str] = []
        for reference in references:
            literal, path = resolve_colour(tokens, str(reference))
            hexes.append(literal)
            paths.append(path)
        for index in range(1, len(hexes)):
            ratio = resolve_pair(hexes[index], hexes[index - 1])
            results.append(
                PairResult(
                    section=f"{SEPARATION_SECTION}.{ramp_name}",
                    foreground_ref=paths[index],
                    background_ref=paths[index - 1],
                    foreground_hex=hexes[index],
                    background_hex=hexes[index - 1],
                    ratio=ratio,
                    required=minimum,
                    sc="1.4.1",
                    note="consecutive chart series separation",
                    passed=ratio >= minimum,
                )
            )
    return results, errors


def check_prohibited(
    tokens: Mapping[str, Any], contract: Json
) -> tuple[list[StaleResult], list[str]]:
    """Assert that each prohibited combination still fails.

    A prohibited entry is documentation with a number attached. If a palette
    change lifts one of these combinations above its asserted maximum, the
    guidance is stale: it tells a designer not to do something that is now fine,
    and it will be ignored, which costs the credibility of the entries that are
    still correct. Reported as a failure so the entry is removed or rewritten in
    the same change that made it obsolete.
    """
    block = contract.get(PROHIBITED_SECTION)
    errors: list[str] = []
    stale: list[StaleResult] = []
    entries: Any = block
    if isinstance(block, Mapping):
        entries = block.get("entries")
    if entries is None:
        return stale, errors
    if not isinstance(entries, Sequence):
        errors.append(f"{PROHIBITED_SECTION}.entries must be a list")
        return stale, errors
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            errors.append(f"{PROHIBITED_SECTION}.entries[{index}] is not an object")
            continue
        for required_key in ("foreground", "background", "maximum"):
            if required_key not in entry:
                errors.append(
                    f"{PROHIBITED_SECTION}.entries[{index}] is missing {required_key!r}"
                )
                continue
        foreground_ref = str(entry["foreground"])
        background_ref = str(entry["background"])
        maximum = float(entry["maximum"])
        foreground_hex, foreground_path = resolve_colour(tokens, foreground_ref)
        background_hex, background_path = resolve_colour(tokens, background_ref)
        ratio = resolve_pair(foreground_hex, background_hex)
        if ratio >= maximum - PROHIBITED_TOLERANCE:
            stale.append(
                StaleResult(
                    foreground_ref=foreground_path,
                    background_ref=background_path,
                    ratio=ratio,
                    asserted_maximum=maximum,
                    reason=str(entry.get("reason", "")),
                )
            )
    return stale, errors


def check_coverage(
    tokens: Mapping[str, Any], verified_foregrounds: set[str]
) -> list[CoverageResult]:
    """Report semantic text roles that no declared pair verifies.

    This is the check that catches an addition rather than a regression. A new
    ``text.something`` role is a new colour a user will read, and if nobody
    declared a pair for it then nobody measured it. The failure is silent in every
    other gate: the token is valid JSON, it resolves, the CSS builds, the page
    renders. Only this check notices.
    """
    missing: list[CoverageResult] = []
    for path in sorted(tokens):
        if ".text." not in f".{path}.":
            continue
        if path not in verified_foregrounds:
            missing.append(
                CoverageResult(
                    token_path=path,
                    reason=(
                        "no declared contrast pair uses this text role as a "
                        "foreground, so its legibility is unverified"
                    ),
                )
            )
    return missing


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_report(
    results: Sequence[PairResult],
    coverage: Sequence[CoverageResult],
    stale: Sequence[StaleResult],
    errors: Sequence[str],
    verbose: bool,
) -> str:
    """Render the human-readable report."""
    lines: list[str] = []
    failures = [result for result in results if not result.passed]
    shown = results if verbose else failures

    lines.append("contrast contract")
    lines.append(f"  pairs checked      {len(results)}")
    lines.append(f"  pairs passing      {len(results) - len(failures)}")
    lines.append(f"  pairs failing      {len(failures)}")
    lines.append(f"  uncovered roles    {len(coverage)}")
    lines.append(f"  stale prohibitions {len(stale)}")
    lines.append(f"  structural errors  {len(errors)}")
    lines.append("")

    if shown:
        lines.append("pairs" if verbose else "failing pairs")
        for result in shown:
            mark = "pass" if result.passed else "FAIL"
            lines.append(
                f"  [{mark}] {result.ratio:6.2f}:1 >= {result.required:4.1f}  "
                f"{result.foreground_hex} on {result.background_hex}  "
                f"({result.section}, SC {result.sc})"
            )
            lines.append(f"         {result.label}")
            if result.note:
                lines.append(f"         note: {result.note}")
        lines.append("")

    if coverage:
        lines.append("text roles with no declared contrast pair")
        for item in coverage:
            lines.append(f"  [FAIL] {item.token_path}")
            lines.append(f"         {item.reason}")
        lines.append("")

    if stale:
        lines.append("prohibited combinations that no longer fail")
        # Named `entry` rather than reusing `item` from the coverage loop above.
        # The two loops iterate different dataclasses, and one name across both
        # leaves the second loop's variable carrying the first loop's type, which
        # is why every attribute access below was reported as missing.
        for entry in stale:
            lines.append(
                f"  [FAIL] {entry.foreground_ref} on {entry.background_ref} now "
                f"measures {entry.ratio:.2f}:1, at or above the asserted maximum "
                f"of {entry.asserted_maximum}:1"
            )
            if entry.reason:
                lines.append(f"         documented reason: {entry.reason}")
            lines.append(
                "         remove the entry or rewrite the guidance in the same "
                "change that made it obsolete"
            )
        lines.append("")

    if errors:
        lines.append("structural errors")
        for error in errors:
            lines.append(f"  [FAIL] {error}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(repo_root: Path, verbose: bool, as_json: bool) -> int:
    """Execute every check and return a process exit code."""
    try:
        tokens, contracts = load_contracts(repo_root)
    except (TokenError, ValueError, OSError) as exc:
        print(f"contrast_check: {exc}", file=sys.stderr)
        return 2

    results: list[PairResult] = []
    errors: list[str] = []
    stale: list[StaleResult] = []

    try:
        for contract in contracts:
            for section in PAIR_SECTIONS:
                results.extend(check_pairs(tokens, contract, section))
            separation_results, separation_errors = check_separation(tokens, contract)
            results.extend(separation_results)
            errors.extend(separation_errors)
            contract_stale, contract_errors = check_prohibited(tokens, contract)
            stale.extend(contract_stale)
            errors.extend(contract_errors)
    except (TokenError, ValueError) as exc:
        print(f"contrast_check: {exc}", file=sys.stderr)
        return 2

    verified_foregrounds = {result.foreground_ref for result in results}
    coverage = check_coverage(tokens, verified_foregrounds)

    if as_json:
        payload = {
            "summary": {
                "pairs_checked": len(results),
                "pairs_failing": sum(1 for r in results if not r.passed),
                "uncovered_text_roles": len(coverage),
                "stale_prohibitions": len(stale),
                "structural_errors": len(errors),
            },
            "pairs": [result.as_dict() for result in results],
            "uncovered_text_roles": [item.as_dict() for item in coverage],
            "stale_prohibitions": [item.as_dict() for item in stale],
            "errors": list(errors),
        }
        print(json.dumps(payload, indent=2, sort_keys=False))
    else:
        print(format_report(results, coverage, stale, errors, verbose), end="")

    failed = (
        sum(1 for result in results if not result.passed)
        + len(coverage)
        + len(stale)
        + len(errors)
    )
    if failed:
        if not as_json:
            print(
                f"{failed} problem(s). Fix the token or the contract; do not "
                "lower a minimum to make this gate pass.",
                file=sys.stderr,
            )
        return 1
    if not as_json:
        print("All declared colour pairs meet their contrast minimums.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contrast_check.py",
        description=(
            "Verify every colour pair declared in the ViaVitae token set against "
            "its WCAG 2.x contrast minimum."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help=(
            "Repository root holding tokens/. Defaults to the parent of this "
            "script's directory, so the tool runs from anywhere."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="List passing pairs as well as failing ones.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable report instead of the human-readable one.",
    )
    arguments = parser.parse_args(argv)

    repo_root: Path = arguments.repo_root
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        print(f"contrast_check: no such directory: {repo_root}", file=sys.stderr)
        return 2

    return run(repo_root, bool(arguments.verbose), bool(arguments.json))


if __name__ == "__main__":
    sys.exit(main())
