#!/usr/bin/env python3
"""Validate the ViaVitae design token set: structure, types, aliases, and drift.

``tools/contrast_check.py`` answers one question — do the colours pass WCAG. This
script answers the others, and there are four of them:

1. **Is every token file structurally valid?** A DTCG tree is either a group or a
   token, and the two are distinguishable only by the presence of ``$value``. A
   node that is ambiguously both, a token with no ``$type``, or a group whose
   child is a bare string all parse as JSON and all break every downstream
   consumer in a different way.

2. **Does every ``$value`` match its declared ``$type``?** ``"$type": "duration"``
   with ``"$value": "200"`` is a number where a time was promised. The error is
   invisible in the token file and surfaces as a silently-ignored CSS declaration
   three build steps later.

3. **Does every alias resolve?** ``{color.palette.gold.500}`` is a promise that a
   token exists at that path. A rename in one file breaks every alias to it, and
   JSON has no compiler to tell you. Cycles are checked for the same reason: a
   token that aliases itself resolves forever.

4. **Have the copies drifted?** Three numbers in this repository exist in more
   than one place, because the places that need them cannot share a source. A
   ``@media (min-width: 1024px)`` condition in CSS cannot read a custom property,
   so the breakpoint is written literally in ``build/css/reset.css`` as well as
   declared in ``tokens/breakpoints.json`` and mirrored into
   ``build/figma-tokens/tokens.json``. Three copies of a number is three
   opportunities for them to disagree, and a disagreement between a design file
   and a shipped page is invisible until a user reports it. This script reads all
   three and fails when they differ.

Usage
-----
    python3 tools/validate_tokens.py                # human-readable report
    python3 tools/validate_tokens.py --json         # machine-readable result
    python3 tools/validate_tokens.py --verbose      # include the passing checks
    python3 tools/validate_tokens.py --repo-root .. # run from another directory

Exit codes
----------
    0  every check passed
    1  at least one check failed
    2  a token file could not be read, or a dependency is missing

Dependencies: ``jsonschema`` for the structural schema. Everything else — alias
resolution, type conformance, the CSS and Figma drift checks — is standard
library, because a parser written here can be read and audited in one sitting
and a dependency cannot.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - the import guard is the point
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Repository layout
# ---------------------------------------------------------------------------

#: Every DTCG token file, in dependency order. All are merged into one
#: namespace for alias resolution, because ``icons.json`` aliases into
#: ``colors.json`` and ``colors.church.json`` aliases into ``colors.json``.
TOKEN_FILES: tuple[str, ...] = (
    "tokens/colors.json",
    "tokens/colors.church.json",
    "tokens/typography.json",
    "tokens/spacing.json",
    "tokens/radius.json",
    "tokens/elevation.json",
    "tokens/motion.json",
    "tokens/breakpoints.json",
    "tokens/icons.json",
)

#: Generated Figma Variables file, in Tokens Studio format.
FIGMA_FILE = "build/figma-tokens/tokens.json"

#: Generated CSS custom properties.
TOKENS_CSS = "build/css/tokens.css"

#: Hand-written base reset. Carries literal media-query conditions, because a
#: CSS custom property cannot appear inside a media query condition.
RESET_CSS = "build/css/reset.css"

#: Keys that are annotations rather than tokens or groups.
RESERVED_KEYS = frozenset({"$description", "$extensions", "$value", "$type"})

#: Top-level bookkeeping block. Not DTCG, ignored by conformant tooling, and
#: excluded from the node grammar by the schema below.
BOOKKEEPING_KEY = "meta"

#: An alias reference, ``{dotted.path}``.
ALIAS_RE = re.compile(r"^\{([A-Za-z0-9_.\-]+)\}$")

#: Any alias occurrence inside a larger string, used to find aliases embedded in
#: a composite value such as a shadow colour or a transition duration.
ALIAS_INLINE_RE = re.compile(r"\{([A-Za-z0-9_.\-]+)\}")

#: A canonical colour: ``#`` then exactly six or eight UPPERCASE hex digits.
#: Lowercase and 3-digit shorthand are rejected on purpose — two spellings of one
#: colour is two things for a designer to grep and two ways for a diff to miss a
#: change.
CANONICAL_COLOUR_RE = re.compile(r"^#[0-9A-F]{6}(?:[0-9A-F]{2})?$")

#: A CSS dimension: a number and a unit.
DIMENSION_RE = re.compile(r"^-?(?:\d+|\d*\.\d+)(?:px|rem|em|ch|ex|%|vw|vh|pt)$")

#: A CSS time.
DURATION_RE = re.compile(r"^-?(?:\d+|\d*\.\d+)(?:ms|s)$")

#: Semantic HTML version, used for ``meta.version``.
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[\w.]+)?$")

#: The CSS ``font-weight`` keywords, all of which DTCG permits alongside a number.
FONT_WEIGHT_KEYWORDS = frozenset(
    {
        "thin",
        "extra-light",
        "light",
        "normal",
        "regular",
        "medium",
        "semi-bold",
        "bold",
        "extra-bold",
        "black",
        "extra-black",
    }
)

#: Properties a ``typography`` composite may carry. DTCG defines the first five;
#: ``textCase`` and ``textDecoration`` are permitted and unused here.
TYPOGRAPHY_PROPERTIES = frozenset(
    {
        "fontFamily",
        "fontSize",
        "fontWeight",
        "letterSpacing",
        "lineHeight",
        "textCase",
        "textDecoration",
        "fontVariantNumeric",
    }
)

#: Properties a ``shadow`` layer must carry.
SHADOW_PROPERTIES = frozenset(
    {"color", "offsetX", "offsetY", "blur", "spread", "inset"}
)

#: Properties a ``transition`` composite must carry.
TRANSITION_REQUIRED = frozenset({"duration", "delay", "timingFunction"})

#: Properties a ``transition`` composite may carry. ``property`` is optional
#: because ``transition.none`` animates nothing and so has no list, but every
#: other named transition carries one: a transition that does not say which CSS
#: properties it animates is the exact defect the group exists to prevent, which
#: is a component hand-assembling ``transition-property`` and quietly omitting
#: one of the properties the design changes.
TRANSITION_PROPERTIES = TRANSITION_REQUIRED | {"property"}

#: The values DTCG allows for ``textCase``, in the order the CSS specification
#: lists them. The rejection message is built from this tuple rather than
#: repeating the four words, so the message cannot drift from the check.
TEXT_CASES = ("uppercase", "lowercase", "capitalize", "none")

#: A CSS property name inside a ``transition.property`` list. Deliberately
#: permissive about vendor prefixes and custom properties, and strict about the
#: characters, so a stray comma or a quoted value is caught.
CSS_PROPERTY_RE = re.compile(r"^(?:-[a-z]+-)?[a-z][a-z0-9-]*$")

#: Breakpoint names that are media queries. ``xs`` is the base and is expressed
#: as the absence of a query, so it is deliberately not in this tuple.
MEDIA_BREAKPOINTS: tuple[str, ...] = ("sm", "md", "lg", "xl", "xxl")

#: Container-query size names, distinct from the container WIDTH names below even
#: though both are emitted as ``--vv-container-*`` in CSS.
CONTAINER_QUERY_SIZES: tuple[str, ...] = ("xs", "sm", "md", "lg", "xl")

#: Container width names.
CONTAINER_WIDTHS: tuple[str, ...] = ("max", "prose", "wide")


Json = Mapping[str, Any]


# ---------------------------------------------------------------------------
# DTCG structural schema
# ---------------------------------------------------------------------------

#: JSON Schema (2020-12) for a token file. Expresses the grammar: a node is
#: either a token, which must carry ``$type`` and ``$value``, or a group, which
#: must not carry ``$value``. ``oneOf`` makes a node that is both — an object
#: carrying ``$value`` *and* an object child — a validation error rather than a
#: silent choice by whichever consumer read it first.
#:
#: Groups and tokens may both carry scalar and array annotations under plain
#: names, which is how this repository documents a scale next to the scale:
#: ``reducedMotion.appliesWhen``, ``container.type``, a shadow's ``level``. An
#: annotation cannot be misread, because it is not an object and carries no
#: ``$value``, so a conformant consumer skips it rather than guessing. What an
#: annotation may NOT be is an object child of a token, and that is the one
#: ambiguity the grammar rejects outright.
DTCG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ViaVitae design token file",
    "type": "object",
    "properties": {
        "$description": {"type": "string"},
        "$extensions": {"type": "object"},
        BOOKKEEPING_KEY: {
            "type": "object",
            "required": ["name", "version", "format", "owner"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "version": {"type": "string", "pattern": SEMVER_RE.pattern},
                "format": {"type": "string", "const": "dtcg-draft"},
                "owner": {"type": "string", "minLength": 1},
                "$description": {"type": "string"},
            },
            "additionalProperties": {"$ref": "#/$defs/annotation"},
        },
    },
    "patternProperties": {r"^(?!meta$)[^$].*$": {"$ref": "#/$defs/node"}},
    "additionalProperties": False,
    "$defs": {
        "annotation": {
            "type": ["string", "number", "boolean", "array", "null"],
            "description": "A non-DTCG annotation. Never an object, so it can "
            "never be mistaken for a token or a group.",
        },
        "node": {"oneOf": [{"$ref": "#/$defs/token"}, {"$ref": "#/$defs/group"}]},
        "token": {
            "type": "object",
            "required": ["$type", "$value"],
            "properties": {
                "$type": {"type": "string", "minLength": 1},
                "$description": {"type": "string"},
                "$extensions": {"type": "object"},
            },
            "patternProperties": {r"^[^$].*$": {"$ref": "#/$defs/annotation"}},
        },
        "group": {
            "type": "object",
            "not": {"required": ["$value"]},
            "minProperties": 1,
            "properties": {
                "$description": {"type": "string"},
                "$type": {"type": "string"},
                "$extensions": {"type": "object"},
            },
            "patternProperties": {
                r"^[^$].*$": {
                    "anyOf": [{"$ref": "#/$defs/node"}, {"$ref": "#/$defs/annotation"}]
                }
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostic:
    """One finding. ``location`` is a file, a token path, or both."""

    check: str
    location: str
    message: str

    def render(self) -> str:
        return f"[{self.check}] {self.location}\n    {self.message}"


@dataclass
class Report:
    """Accumulates diagnostics and the passing-check notes for ``--verbose``."""

    failures: list[Diagnostic] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def fail(self, check: str, location: str, message: str) -> None:
        """Record a failure, ignoring an exact repeat.

        Several checks read the same file independently — the namespace loader,
        the schema validator and the drift checks each parse what they need — so
        one malformed file is seen more than once. Reporting it once is the
        difference between a readable report and three copies of the same line,
        which is how a real second defect gets scrolled past.
        """
        diagnostic = Diagnostic(check, location, message)
        if diagnostic not in self.failures:
            self.failures.append(diagnostic)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def count(self, key: str, amount: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + amount

    @property
    def ok(self) -> bool:
        return not self.failures


class TokenError(Exception):
    """Raised when a token file cannot be read at all, as opposed to being wrong."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    """``object_pairs_hook`` that fails on a repeated key.

    ``json.load`` silently keeps the last of two identical keys, so a token file
    with ``"gold"`` declared twice parses cleanly and ships one of them. Which
    one is an implementation detail of the parser. Rejecting the file is the only
    behaviour that does not depend on one.
    """
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen[key] = value
    return seen


def load_json_strict(path: Path) -> Any:
    """Parse a JSON file, rejecting duplicate object keys.

    Raises :class:`TokenError` naming the file and the byte offset, because a
    parse failure in a generated file has to be traceable to the generator.
    """
    if not path.is_file():
        raise TokenError(f"missing file: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise TokenError(f"{path} is not valid UTF-8: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise TokenError(
            f"{path} is not valid JSON: line {exc.lineno} column {exc.colno}: {exc.msg}"
        ) from exc
    except ValueError as exc:
        raise TokenError(f"{path.name} contains a repeated object key ({exc})") from exc


def walk_tokens(node: Any, prefix: str = "") -> Iterator[tuple[str, Json]]:
    """Yield ``(dotted.path, token)`` for every token in a DTCG tree.

    A node carrying ``$value`` is a token and is yielded without descending: in
    DTCG a token cannot have children, so anything below ``$value`` is an
    annotation on that token rather than a further token.
    """
    if not isinstance(node, Mapping):
        return
    if "$value" in node:
        if prefix:
            yield prefix, node
        return
    for key, child in node.items():
        if key.startswith("$") or key == BOOKKEEPING_KEY:
            continue
        yield from walk_tokens(child, f"{prefix}.{key}" if prefix else key)


def load_token_namespace(repo_root: Path, report: Report) -> dict[str, Any]:
    """Merge every token file into one flat ``{dotted.path: token}`` namespace.

    A top-level key declared by two files is an error rather than an overwrite:
    two files claiming the same root means one of them is wrong about what it
    owns, and the merge order would decide the outcome.
    """
    roots: dict[str, tuple[str, Any]] = {}
    tokens: dict[str, Any] = {}
    for relative in TOKEN_FILES:
        path = repo_root / relative
        try:
            document = load_json_strict(path)
        except TokenError as exc:
            report.fail("parse", relative, str(exc))
            continue
        if not isinstance(document, dict):
            report.fail(
                "parse", relative, "the root of a token file must be a JSON object"
            )
            continue
        report.count("files")
        for key, value in document.items():
            if key.startswith("$") or key == BOOKKEEPING_KEY:
                continue
            if key in roots:
                report.fail(
                    "namespace",
                    relative,
                    f"top-level key {key!r} is also declared in {roots[key][0]}; "
                    "each root is owned by exactly one file",
                )
                continue
            roots[key] = (relative, value)
        for token_path, token in walk_tokens(document):
            tokens[token_path] = token
            report.count("tokens")
    return tokens


# ---------------------------------------------------------------------------
# Type conformance
# ---------------------------------------------------------------------------


def _is_alias(value: Any) -> bool:
    """True when ``value`` is ``{some.path}`` and therefore not yet a literal.

    An alias is type-checked after resolution, not here: the resolved target
    carries the authoritative ``$type``, and checking the reference itself would
    mean rejecting every correctly-written alias in the system.
    """
    return isinstance(value, str) and ALIAS_RE.match(value) is not None


def _contains_alias(value: Any) -> bool:
    """True when ``value`` embeds an alias anywhere, including inside a composite."""
    if isinstance(value, str):
        return ALIAS_INLINE_RE.search(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_alias(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_alias(item) for item in value)
    return False


def check_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return "a colour must be a string"
    if not CANONICAL_COLOUR_RE.match(value):
        return (
            f"{value!r} is not a canonical colour: expected '#RRGGBB' or "
            "'#RRGGBBAA' with uppercase hex digits"
        )
    return None


def check_dimension(value: Any) -> str | None:
    if not isinstance(value, str):
        return "a dimension must be a string carrying a unit"
    if not DIMENSION_RE.match(value):
        return (
            f"{value!r} is not a CSS dimension: expected a number followed by one "
            "of px, rem, em, ch, ex, %, vw, vh, pt"
        )
    return None


def check_duration(value: Any) -> str | None:
    if not isinstance(value, str):
        return "a duration must be a string carrying a unit"
    if not DURATION_RE.match(value):
        return f"{value!r} is not a CSS time: expected a number followed by ms or s"
    return None


def check_font_family(value: Any) -> str | None:
    names = value if isinstance(value, list) else [value]
    if not isinstance(value, (list, str)):
        return "a font family must be a string or an array of strings"
    if isinstance(value, list) and not value:
        return "a font family stack must not be empty"
    for name in names:
        if not isinstance(name, str) or not name.strip():
            return f"{name!r} is not a usable font family name"
    if isinstance(value, list):
        generic = value[-1].strip().lower().strip("'\"")
        if generic not in {
            "serif",
            "sans-serif",
            "monospace",
            "cursive",
            "fantasy",
            "system-ui",
            "ui-serif",
            "ui-sans-serif",
            "ui-monospace",
            "ui-rounded",
            "math",
            "emoji",
            "fangsong",
        }:
            return (
                f"the stack ends with {value[-1]!r}, which is not a CSS generic "
                "family; without one the fallback is browser-dependent and "
                "therefore untestable"
            )
    return None


def check_font_weight(value: Any) -> str | None:
    if isinstance(value, bool):
        return "a font weight must be a number or a CSS keyword, not a boolean"
    if isinstance(value, (int, float)):
        if not 1 <= value <= 1000:
            return f"{value} is outside the CSS font-weight range 1-1000"
        return None
    if isinstance(value, str):
        if value in FONT_WEIGHT_KEYWORDS:
            return None
        return f"{value!r} is neither a number nor a CSS font-weight keyword"
    return "a font weight must be a number or a CSS keyword"


def check_cubic_bezier(value: Any) -> str | None:
    if not isinstance(value, list) or len(value) != 4:
        return "a cubic-bezier must be an array of exactly four numbers"
    for index, point in enumerate(value):
        if isinstance(point, bool) or not isinstance(point, (int, float)):
            return f"cubic-bezier control point {index} is {point!r}, not a number"
        if index in (0, 2) and not 0.0 <= point <= 1.0:
            return (
                f"cubic-bezier control point {index} is {point}: the x coordinates "
                "of a CSS timing function must lie in [0, 1], or the curve is not "
                "a function of time"
            )
    return None


def check_number(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{value!r} is not a number"
    return None


def check_boolean(value: Any) -> str | None:
    if not isinstance(value, bool):
        return f"{value!r} is not a boolean"
    return None


def check_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return f"{value!r} is not a string"
    if not value.strip():
        return "a string token must not be empty or whitespace"
    return None


def check_font_variant(value: Any) -> str | None:
    if not isinstance(value, str):
        return "a font-variant token must be a string"
    permitted = {
        "normal",
        "none",
        "tabular-nums",
        "proportional-nums",
        "lining-nums",
        "oldstyle-nums",
        "slashed-zero",
        "common-ligatures",
        "no-common-ligatures",
        "discretionary-ligatures",
        "no-discretionary-ligatures",
        "historical-ligatures",
        "no-historical-ligatures",
        "contextual",
        "no-contextual",
        "small-caps",
        "all-small-caps",
        "petite-caps",
        "unicase",
        "titling-caps",
    }
    for part in value.split():
        if part not in permitted:
            return f"{part!r} is not a CSS font-variant keyword"
    return None


def _check_shadow_layer(layer: Any) -> str | None:
    if not isinstance(layer, Mapping):
        return "a shadow layer must be an object"
    missing = SHADOW_PROPERTIES - set(layer)
    if missing:
        return f"a shadow layer is missing {', '.join(sorted(missing))}"
    extra = set(layer) - SHADOW_PROPERTIES
    if extra:
        return f"a shadow layer carries unknown properties: {', '.join(sorted(extra))}"
    if check_color(layer["color"]) is not None and not _contains_alias(layer["color"]):
        return f"shadow colour {layer['color']!r} is not a canonical colour"
    for key in ("offsetX", "offsetY", "blur", "spread"):
        if _contains_alias(layer[key]):
            continue
        problem = check_dimension(layer[key])
        if problem:
            return f"shadow {key}: {problem}"
    if not isinstance(layer["inset"], bool):
        return f"shadow 'inset' must be a boolean, got {layer['inset']!r}"
    return None


def check_shadow(value: Any) -> str | None:
    layers = value if isinstance(value, list) else [value]
    if not isinstance(value, (list, Mapping)):
        return "a shadow must be an object or an array of objects"
    if isinstance(value, list) and not value:
        return "a shadow array must not be empty"
    for index, layer in enumerate(layers):
        problem = _check_shadow_layer(layer)
        if problem:
            return f"layer {index}: {problem}" if isinstance(value, list) else problem
    return None


def check_typography(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return "a typography composite must be an object"
    unknown = set(value) - TYPOGRAPHY_PROPERTIES
    if unknown:
        return (
            f"unknown typography properties: {', '.join(sorted(unknown))}. The DTCG "
            "name for a CSS text-transform is 'textCase'; a property name taken "
            "straight from CSS is a deviation from the declared format"
        )
    for required in ("fontFamily", "fontSize", "fontWeight", "lineHeight"):
        if required not in value:
            return f"a typography composite is missing {required!r}"
    size = value["fontSize"]
    if not _contains_alias(size):
        problem = check_dimension(size)
        if problem:
            return f"fontSize: {problem}"
    spacing = value.get("letterSpacing")
    if spacing is not None and not _contains_alias(spacing) and spacing != "normal":
        problem = check_dimension(spacing)
        if problem:
            return f"letterSpacing: {problem}"
    line_height = value["lineHeight"]
    if not _contains_alias(line_height):
        problem = check_number(line_height)
        if problem:
            return f"lineHeight: {problem}"
        elif not 0.5 <= line_height <= 4.0:
            return (
                f"lineHeight {line_height} is a suspicious unitless multiplier; a "
                "value below 0.5 or above 4 is almost always a pixel figure that "
                "lost its unit, and a unitless multiplier is what makes the line "
                "box scale with a user's font-size preference"
            )
    case = value.get("textCase")
    if case is not None and not _contains_alias(case) and case not in TEXT_CASES:
        return f"textCase {case!r} is not one of {', '.join(TEXT_CASES)}"
    return None


def check_transition(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return "a transition composite must be an object"
    missing = TRANSITION_REQUIRED - set(value)
    if missing:
        return f"a transition composite is missing {', '.join(sorted(missing))}"
    extra = set(value) - TRANSITION_PROPERTIES
    if extra:
        return f"a transition composite carries unknown properties: {', '.join(sorted(extra))}"
    for key in ("duration", "delay"):
        if key not in value or _contains_alias(value[key]):
            continue
        problem = check_duration(value[key])
        if problem:
            return f"{key}: {problem}"
    properties = value.get("property")
    if properties is not None and not _contains_alias(properties):
        if not isinstance(properties, str):
            return "transition 'property' must be a comma-separated string"
        for name in (item.strip() for item in properties.split(",")):
            if not CSS_PROPERTY_RE.match(name):
                return f"transition property {name!r} is not a CSS property name"
    return None


#: ``$type`` to validator. Every type the token set actually uses appears here;
#: :func:`check_types` reports an unknown ``$type`` rather than skipping it, so a
#: new type added to a token file without a validator is a build failure and not
#: a silent gap in coverage.
TYPE_CHECKS: dict[str, Callable[[Any], str | None]] = {
    "color": check_color,
    "dimension": check_dimension,
    "duration": check_duration,
    "fontFamily": check_font_family,
    "fontWeight": check_font_weight,
    "fontVariantNumeric": check_font_variant,
    "fontVariantLigatures": check_font_variant,
    "cubicBezier": check_cubic_bezier,
    "number": check_number,
    "boolean": check_boolean,
    "string": check_string,
    "shadow": check_shadow,
    "typography": check_typography,
    "transition": check_transition,
}


def check_types(tokens: Mapping[str, Json], report: Report) -> None:
    """Validate every literal ``$value`` against its declared ``$type``."""
    for path, token in sorted(tokens.items()):
        declared = token.get("$type")
        value = token.get("$value")
        if _is_alias(value) or _contains_alias(value):
            # Resolved and re-checked by check_aliases, which sees the whole
            # composite with every reference substituted.
            continue
        validator = TYPE_CHECKS.get(declared)
        if validator is None:
            report.fail(
                "type",
                path,
                f"$type {declared!r} has no validator in TYPE_CHECKS; add one "
                "rather than letting an unvalidated type through the gate",
            )
            continue
        problem = validator(value)
        if problem:
            report.fail("type", path, f"$type {declared!r}: {problem}")
        else:
            report.count("typed")


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------


def resolve_alias(
    tokens: Mapping[str, Json], reference: str, chain: tuple[str, ...] = ()
) -> tuple[Any, str]:
    """Follow ``reference`` to the literal token it names.

    Returns ``(value, resolved_path)``. Raises :class:`TokenError` for a missing
    target, for a target that is itself a group rather than a token, and for a
    cycle — the cycle message names the whole chain, because "circular reference"
    without the path is a finding nobody can act on.
    """
    if reference in chain:
        raise TokenError("circular alias: " + " -> ".join(chain + (reference,)))
    target = tokens.get(reference)
    if target is None:
        raise TokenError(f"no token at {reference!r}")
    value = target.get("$value")
    if _is_alias(value):
        inner = ALIAS_RE.match(value).group(1)
        return resolve_alias(tokens, inner, chain + (reference,))
    return value, reference


def substitute(value: Any, tokens: Mapping[str, Json], chain: tuple[str, ...]) -> Any:
    """Return ``value`` with every embedded alias replaced by its resolved value.

    Composites carry aliases inside them — a shadow's ``color``, a transition's
    ``duration`` — so substitution has to recurse rather than only handling the
    case where the whole ``$value`` is a reference.
    """
    if isinstance(value, str):
        match = ALIAS_RE.match(value)
        if match is not None:
            resolved, path = resolve_alias(tokens, match.group(1), chain)
            return substitute(resolved, tokens, chain + (path,))
        return ALIAS_INLINE_RE.sub(
            lambda found: str(resolve_alias(tokens, found.group(1), chain)[0]), value
        )
    if isinstance(value, Mapping):
        return {key: substitute(item, tokens, chain) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, tokens, chain) for item in value]
    return value


def check_aliases(tokens: Mapping[str, Json], report: Report) -> None:
    """Resolve every alias, then type-check the fully substituted composite.

    A token whose ``$value`` contains an alias is skipped by :func:`check_types`,
    because at that point the value is a reference and not a literal. This is
    where those tokens are checked: the composite is resolved end to end and the
    result is validated against the declared type, which is the only point at
    which ``{"duration": "{duration.instant}"}`` can be confirmed to be a time.
    """
    for path, token in sorted(tokens.items()):
        value = token.get("$value")
        if not _contains_alias(value):
            continue
        try:
            resolved = substitute(value, tokens, (path,))
        except TokenError as exc:
            report.fail("alias", path, f"$value {value!r}: {exc}")
            continue
        declared_type = token.get("$type")
        validator = TYPE_CHECKS.get(declared_type) if isinstance(declared_type, str) else None
        if validator is None:
            report.fail(
                "alias",
                path,
                f"$type {declared_type!r} has no validator in TYPE_CHECKS",
            )
            continue
        problem = validator(resolved)
        if problem:
            report.fail(
                "alias",
                path,
                f"resolves to {json.dumps(resolved)} which fails $type "
                f"{declared_type!r}: {problem}",
            )
        else:
            report.count("aliased")


# ---------------------------------------------------------------------------
# Structural and bookkeeping checks
# ---------------------------------------------------------------------------


def check_structure(repo_root: Path, report: Report) -> None:
    """Run the DTCG JSON Schema over every token file."""
    if jsonschema is None:
        report.fail(
            "structure",
            "tools/requirements.txt",
            "jsonschema is not installed, so the structural grammar cannot be "
            "checked. Run: pip install -r tools/requirements.txt",
        )
        return
    validator = jsonschema.Draft202012Validator(DTCG_SCHEMA)
    for relative in TOKEN_FILES:
        path = repo_root / relative
        if not path.is_file():
            report.fail("structure", relative, "file is missing")
            continue
        try:
            document = load_json_strict(path)
        except TokenError:
            continue  # already reported by load_token_namespace
        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        for error in errors[:20]:
            location = ".".join(str(part) for part in error.path) or "<root>"
            report.fail("structure", f"{relative}:{location}", error.message)
        if len(errors) > 20:
            report.fail(
                "structure",
                relative,
                f"{len(errors) - 20} further schema errors omitted",
            )
        if not errors:
            report.count("structured")


def check_bookkeeping(repo_root: Path, report: Report) -> None:
    """Require a ``meta`` block in every file and a single version across them.

    A token set with no declared version cannot be diffed against a release, and
    nine files declaring nine versions cannot be released as one. Both are
    cheap to enforce and expensive to reconstruct after the fact.
    """
    versions: dict[str, str] = {}
    for relative in TOKEN_FILES:
        path = repo_root / relative
        if not path.is_file():
            continue
        try:
            document = load_json_strict(path)
        except TokenError:
            continue
        meta = document.get(BOOKKEEPING_KEY)
        if not isinstance(meta, Mapping):
            report.fail(
                "meta",
                relative,
                f"no {BOOKKEEPING_KEY!r} block; every token file declares name, version, format and owner",
            )
            continue
        version = meta.get("version")
        if isinstance(version, str):
            versions[relative] = version
        owner = meta.get("owner")
        if owner != "@Via-Vitae/brand":
            report.fail(
                "meta", relative, f"owner is {owner!r}; expected '@Via-Vitae/brand'"
            )
    distinct = sorted(set(versions.values()))
    if len(distinct) > 1:
        detail = ", ".join(
            f"{name}={value}" for name, value in sorted(versions.items())
        )
        report.fail(
            "meta",
            "tokens/",
            f"token files declare more than one version ({', '.join(distinct)}): {detail}. "
            "The set ships as one artefact and carries one version.",
        )
    elif distinct:
        report.note(f"all {len(versions)} token files declare version {distinct[0]}")


# ---------------------------------------------------------------------------
# CSS and Figma extraction
# ---------------------------------------------------------------------------

CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CUSTOM_PROPERTY_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+);")
MIN_WIDTH_QUERY_RE = re.compile(r"@media[^{]*?\(min-width:\s*(\d+)px\s*\)")
CONTAINER_QUERY_RE = re.compile(r"@container[^{]*?\(min-width:\s*(\d+)px\s*\)")


def strip_css_comments(text: str) -> str:
    """Remove CSS block comments so prose cannot be read as a declaration.

    The guidelines and the CSS headers quote values in prose. Matching against
    the raw text would treat a documented example as a declaration and either
    pass a real drift or invent a false one.
    """
    return CSS_COMMENT_RE.sub(" ", text)


def read_css(repo_root: Path, relative: str, report: Report) -> str | None:
    path = repo_root / relative
    if not path.is_file():
        report.fail("drift", relative, "file is missing; the drift check cannot run")
        return None
    return strip_css_comments(path.read_text(encoding="utf-8"))


def extract_custom_properties(text: str) -> dict[str, set[str]]:
    """Collect ``{property-name: {every value it is declared with}}``.

    A set rather than a last-wins map, because ``build/css/tokens.css`` declares
    the same property more than once by design — once inside ``:root`` as a
    ``light-dark()`` pair and again inside the ``@supports not`` fallback for
    browsers without it. Both declarations must carry the same literal, and a set
    is what makes "the same literal" checkable.
    """
    found: dict[str, set[str]] = {}
    for name, value in CUSTOM_PROPERTY_RE.findall(text):
        found.setdefault(name.strip(), set()).add(value.strip())
    return found


def pixels(values: set[str]) -> set[int]:
    """Reduce a set of ``NNNpx`` declarations to the integers they name."""
    out: set[int] = set()
    for value in values:
        match = re.fullmatch(r"(\d+)px", value)
        if match:
            out.add(int(match.group(1)))
    return out


def walk_studio_tokens(node: Any, prefix: str = "") -> Iterator[tuple[str, Json]]:
    """Yield ``(dotted.path, token)`` for a Tokens Studio file.

    The plugin format predates DTCG and spells the same two fields ``value`` and
    ``type``. A separate walker rather than a parameterised one: the two formats
    differ in more than the key names (``$metadata`` and ``$themes`` have no DTCG
    counterpart) and a shared walker would need enough conditionals to be harder
    to read than two short ones.
    """
    if not isinstance(node, Mapping):
        return
    if "value" in node and "type" in node:
        if prefix:
            yield prefix, node
        return
    for key, child in node.items():
        if key.startswith("$"):
            continue
        yield from walk_studio_tokens(child, f"{prefix}.{key}" if prefix else key)


def load_studio_file(repo_root: Path, report: Report) -> dict[str, Json] | None:
    path = repo_root / FIGMA_FILE
    try:
        document = load_json_strict(path)
    except TokenError as exc:
        report.fail("drift", FIGMA_FILE, str(exc))
        return None
    return dict(walk_studio_tokens(document))


def studio_literal(token: Json, studio: Mapping[str, Json]) -> Any:
    """Resolve a Tokens Studio alias (``{global.color.ivory.100}``) to a literal."""
    value = token.get("value")
    seen: set[str] = set()
    while isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        reference = value[1:-1]
        if reference in seen:
            return value
        seen.add(reference)
        target = studio.get(reference)
        if target is None:
            return value
        value = target.get("value")
    return value


def as_int(value: Any) -> int | None:
    """Coerce a Figma numeric string (``"1024"``) or a CSS length to an integer."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        match = re.fullmatch(r"(\d+)(?:px)?", text)
        if match:
            return int(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Colour drift: tokens/ against the generated Figma file
# ---------------------------------------------------------------------------

#: Figma-only palette entries and the source token each one mirrors. The Figma
#: ``global`` set needs a bare white and two scrims as aliasable variables, while
#: the DTCG source declares them in the roles that use them. The pairing is
#: written out rather than inferred, so adding a fourth entry without declaring
#: its provenance is a build failure.
FIGMA_ONLY_COLOURS: tuple[tuple[str, str], ...] = (
    ("global.color.white", "color.semantic.light.surface.raised"),
    ("global.color.scrim-light", "color.semantic.light.surface.overlay"),
    ("global.color.scrim-dark", "color.semantic.dark.surface.overlay"),
)

#: Prefix pairs where the Figma path is the source path with the head replaced.
COLOUR_PREFIX_MAP: tuple[tuple[str, str], ...] = (
    ("color.palette.", "global.color."),
    ("color.semantic.light.", "semantic-light."),
    ("color.semantic.dark.", "semantic-dark."),
    ("color.church.", "church-context."),
    ("season.", "liturgical-season."),
)

#: Chart chrome is grouped per theme in the Figma file and suffixed per theme in
#: the DTCG source, because Figma Variables switch by mode while a CSS custom
#: property switches by ``light-dark()``. Neither spelling is wrong; the mapping
#: has to be explicit or the two look like they disagree.
CHART_CHROME_MAP: dict[str, str] = {
    "color.chart.grid": "chart.light.grid",
    "color.chart.axis": "chart.light.axis",
    "color.chart.label": "chart.light.label",
    "color.chart.grid-dark": "chart.dark.grid",
    "color.chart.axis-dark": "chart.dark.axis",
    "color.chart.label-dark": "chart.dark.label",
}


def figma_path_for(source_path: str) -> str | None:
    """Return the Figma path that must mirror ``source_path``, or ``None``.

    ``None`` means the source token is not exported to Figma at all, which is
    true of a small number of documentation-only tokens and is not an error.
    """
    if source_path in CHART_CHROME_MAP:
        return CHART_CHROME_MAP[source_path]
    match = re.match(r"^color\.chart\.(light|dark)\.(\d+)$", source_path)
    if match:
        return f"chart.{match.group(1)}.{match.group(2)}"
    for source_prefix, figma_prefix in COLOUR_PREFIX_MAP:
        if source_path.startswith(source_prefix):
            return figma_prefix + source_path[len(source_prefix) :]
    return None


def collect_source_colours(
    tokens: Mapping[str, Json], report: Report
) -> dict[str, str]:
    """Resolve every ``$type: color`` token in ``tokens/`` to a literal hex.

    Called once per run and shared by the Figma and CSS comparisons, so an
    unresolvable alias is reported once rather than once per consumer.
    """
    resolved: dict[str, str] = {}
    for path, token in sorted(tokens.items()):
        if token.get("$type") != "color":
            continue
        try:
            value = substitute(token.get("$value"), tokens, (path,))
        except TokenError as exc:
            report.fail("alias", path, f"cannot resolve to a literal colour: {exc}")
            continue
        if not isinstance(value, str):
            report.fail("drift", path, f"resolved to {value!r}, not a colour string")
            continue
        resolved[path] = value.upper()
    return resolved


def collect_studio_colours(
    studio: Mapping[str, Json], report: Report
) -> dict[str, str]:
    """Resolve every ``type: color`` token in the Figma file to a literal hex."""
    resolved: dict[str, str] = {}
    for path, token in sorted(studio.items()):
        if token.get("type") != "color":
            continue
        value = studio_literal(token, studio)
        if not isinstance(value, str):
            report.fail(
                "drift",
                f"{FIGMA_FILE}:{path}",
                f"value is {value!r}, not a colour string; an unresolvable alias "
                "lands in Figma as a literal reference that silently never updates",
            )
            continue
        resolved[path] = value.upper()
    return resolved


def check_colour_drift(
    repo_root: Path, source: Mapping[str, str], report: Report
) -> None:
    """Compare every colour token in ``tokens/`` against the generated Figma copy.

    Run in both directions. A value that differs is drift; a token present on one
    side only is an omission, and an omission is the more dangerous of the two,
    because a Figma variable that does not exist is one a designer fills in by
    hand and then defends as correct.
    """
    studio = load_studio_file(repo_root, report)
    if studio is None:
        return
    figma = collect_studio_colours(studio, report)

    expected_of_figma: dict[str, str] = {}
    for path, hex_value in source.items():
        target = figma_path_for(path)
        if target is None:
            continue
        expected_of_figma[target] = path
        if target not in figma:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:{target}",
                f"absent, but {path} declares {hex_value}; regenerate with "
                "python3 tools/build_exports.py --figma",
            )
            continue
        if figma[target] != hex_value:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:{target}",
                f"is {figma[target]} but the source {path} is {hex_value}",
            )
        else:
            report.count("colours")

    for figma_path, source_path in FIGMA_ONLY_COLOURS:
        if figma_path not in figma:
            report.fail(
                "drift", f"{FIGMA_FILE}:{figma_path}", "absent from the Figma palette"
            )
            continue
        if source_path not in source:
            report.fail(
                "drift",
                source_path,
                f"absent, but {FIGMA_FILE} mirrors it at {figma_path}",
            )
            continue
        expected_of_figma[figma_path] = source_path
        if figma[figma_path] != source[source_path]:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:{figma_path}",
                f"is {figma[figma_path]} but the source {source_path} is {source[source_path]}",
            )
        else:
            report.count("colours")

    orphans = sorted(set(figma) - set(expected_of_figma))
    for path in orphans:
        report.fail(
            "drift",
            f"{FIGMA_FILE}:{path}",
            f"is {figma[path]} but no token in tokens/ maps to it; either it was "
            "hand-edited into the generated file or its source token was renamed",
        )


# ---------------------------------------------------------------------------
# Numeric drift: breakpoints, containers, durations, easings
# ---------------------------------------------------------------------------


def load_raw(repo_root: Path, relative: str, report: Report) -> Any:
    path = repo_root / relative
    try:
        return load_json_strict(path)
    except TokenError as exc:
        report.fail("parse", relative, str(exc))
        return None


def check_breakpoint_drift(
    repo_root: Path, tokens: Mapping[str, Json], report: Report
) -> None:
    """Compare the four copies of every breakpoint and container width.

    ``tokens/breakpoints.json`` and ``tokens/spacing.json`` are the source. Three
    copies follow, and each exists because the format that needs it cannot read
    the source: a CSS media query condition cannot contain a custom property, and
    a Figma Variable cannot contain a reference to a JSON file.

    The check runs in the direction that catches an invention. A literal
    ``@media (min-width: 900px)`` in the shipped CSS with no token behind it is a
    breakpoint nobody designed, tested or reviewed, and it is the failure this
    exists for. The reverse — a declared breakpoint the reset never queries — is
    reported as a note rather than an error, because a base reset is not obliged
    to use every step the system defines.
    """
    tokens_css = read_css(repo_root, TOKENS_CSS, report)
    reset_css = read_css(repo_root, RESET_CSS, report)
    studio = load_studio_file(repo_root, report)
    if tokens_css is None or reset_css is None or studio is None:
        return
    properties = extract_custom_properties(tokens_css)

    declared: dict[str, int] = {}
    for name in MEDIA_BREAKPOINTS:
        token = tokens.get(f"breakpoint.{name}")
        if token is None:
            report.fail(
                "drift", f"tokens/breakpoints.json:breakpoint.{name}", "missing"
            )
            continue
        value = as_int(token.get("$value"))
        if value is None:
            report.fail(
                "drift",
                f"tokens/breakpoints.json:breakpoint.{name}",
                f"$value {token.get('$value')!r} is not a pixel length",
            )
            continue
        declared[name] = value

    base = tokens.get("breakpoint.xs")
    if base is None or as_int(base.get("$value")) != 0:
        report.fail(
            "drift",
            "tokens/breakpoints.json:breakpoint.xs",
            "the base step must be 0px; it is expressed as the absence of a query",
        )

    for name, value in sorted(declared.items()):
        css_values = properties.get(f"--vv-breakpoint-{name}", set())
        if not css_values:
            report.fail("drift", f"{TOKENS_CSS}:--vv-breakpoint-{name}", "not declared")
        elif css_values != {f"{value}px"}:
            report.fail(
                "drift",
                f"{TOKENS_CSS}:--vv-breakpoint-{name}",
                f"declared as {', '.join(sorted(css_values))} but breakpoint.{name} is {value}px",
            )
        else:
            report.count("breakpoints")

        figma_token = studio.get(f"layout.breakpoint.{name}")
        if figma_token is None:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:layout.breakpoint.{name}",
                "absent; a Figma frame would be built at a width no CSS query matches",
            )
        elif as_int(studio_literal(figma_token, studio)) != value:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:layout.breakpoint.{name}",
                f"is {figma_token.get('value')!r} but breakpoint.{name} is {value}",
            )
        else:
            report.count("breakpoints")

    queries = {int(match) for match in MIN_WIDTH_QUERY_RE.findall(reset_css)}
    invented = sorted(queries - set(declared.values()))
    for width in invented:
        report.fail(
            "drift",
            f"{RESET_CSS}:@media (min-width: {width}px)",
            f"{width}px is not a declared breakpoint ({', '.join(str(v) for v in sorted(declared.values()))}); "
            "an undeclared breakpoint is a layout nobody designed, tested or reviewed",
        )
    unused = sorted(set(declared.values()) - queries)
    if unused:
        report.note(
            f"{RESET_CSS} declares no min-width query at "
            f"{', '.join(str(width) + 'px' for width in unused)}; permitted, since a "
            "base reset need not use every step the system defines"
        )
    if not invented:
        report.count("queries", len(queries))

    for name in CONTAINER_WIDTHS:
        token = tokens.get(f"layout.container-{name}")
        if token is None:
            report.fail(
                "drift", f"tokens/spacing.json:layout.container-{name}", "missing"
            )
            continue
        value = as_int(token.get("$value"))
        css_values = properties.get(f"--vv-container-{name}", set())
        if css_values != {f"{value}px"}:
            report.fail(
                "drift",
                f"{TOKENS_CSS}:--vv-container-{name}",
                f"declared as {', '.join(sorted(css_values)) or 'absent'} but "
                f"layout.container-{name} is {value}px",
            )
        else:
            report.count("containers")
        figma_token = studio.get(f"layout.container.{name}")
        if figma_token is None or as_int(studio_literal(figma_token, studio)) != value:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:layout.container.{name}",
                f"is {figma_token.get('value') if figma_token else 'absent'} but "
                f"layout.container-{name} is {value}",
            )
        else:
            report.count("containers")

    for name in CONTAINER_QUERY_SIZES:
        token = tokens.get(f"container.sizes.{name}")
        if token is None:
            report.fail(
                "drift", f"tokens/breakpoints.json:container.sizes.{name}", "missing"
            )
            continue
        value = as_int(token.get("$value"))
        css_values = properties.get(f"--vv-container-{name}", set())
        if css_values != {f"{value}px"}:
            report.fail(
                "drift",
                f"{TOKENS_CSS}:--vv-container-{name}",
                f"declared as {', '.join(css_values) or 'absent'} but "
                f"container.sizes.{name} is {value}px",
            )
        else:
            report.count("containers")

    breakpoints_file = load_raw(repo_root, "tokens/breakpoints.json", report)
    if isinstance(breakpoints_file, Mapping):
        minimum = (
            breakpoints_file.get("$extensions", {})
            .get("com.viavitae.minimum", {})
            .get("minimumViewportWidth")
        )
        figma_token = studio.get("layout.breakpoint.minimum-viewport")
        if as_int(minimum) is None:
            report.fail(
                "drift",
                "tokens/breakpoints.json:$extensions.com.viavitae.minimum",
                f"minimumViewportWidth is {minimum!r}, not a pixel length",
            )
        elif figma_token is None or as_int(
            studio_literal(figma_token, studio)
        ) != as_int(minimum):
            report.fail(
                "drift",
                f"{FIGMA_FILE}:layout.breakpoint.minimum-viewport",
                f"is {figma_token.get('value') if figma_token else 'absent'} but the "
                f"source declares {minimum}; this is the WCAG 1.4.10 Reflow width",
            )
        else:
            report.count("breakpoints")


CUBIC_BEZIER_CSS_RE = re.compile(
    r"^cubic-bezier\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)$"
)


def check_motion_drift(
    repo_root: Path, tokens: Mapping[str, Json], report: Report
) -> None:
    """Compare durations and easing curves against the Figma copy.

    Easings are worth the effort: Figma's own easing presets do not coincide with
    these curves, so a prototype built on a preset looks close and ships wrong,
    and "close" is exactly the case a reviewer waves through.
    """
    studio = load_studio_file(repo_root, report)
    if studio is None:
        return

    source_durations = {
        path[len("duration.") :]: token
        for path, token in tokens.items()
        if path.startswith("duration.") and token.get("$type") == "duration"
    }
    figma_durations = {
        path[len("motion.duration.") :]: token
        for path, token in studio.items()
        if path.startswith("motion.duration.")
    }
    reduced = tokens.get("reducedMotion.duration")
    if reduced is not None:
        source_durations["reduced-motion"] = reduced

    for name in sorted(set(source_durations) | set(figma_durations)):
        source_token = source_durations.get(name)
        figma_token = figma_durations.get(name)
        if source_token is None or figma_token is None:
            report.fail(
                "drift",
                f"motion.duration.{name}",
                "declared in only one of tokens/motion.json and "
                f"{FIGMA_FILE}:motion.duration",
            )
            continue
        source_value = source_token.get("$value")
        match = re.fullmatch(r"([\d.]+)ms", str(source_value))
        if match is None:
            report.fail(
                "drift",
                f"tokens/motion.json:{name}",
                f"$value {source_value!r} is not a whole-millisecond duration, so it "
                "cannot be expressed as the number Figma needs",
            )
            continue
        if as_int(studio_literal(figma_token, studio)) != int(float(match.group(1))):
            report.fail(
                "drift",
                f"{FIGMA_FILE}:motion.duration.{name}",
                f"is {figma_token.get('value')!r} but the source is {source_value}",
            )
        else:
            report.count("durations")

    source_easings = {
        path[len("easing.") :]: token
        for path, token in tokens.items()
        if path.startswith("easing.") and token.get("$type") == "cubicBezier"
    }
    figma_easings = {
        path[len("motion.easing.") :]: token
        for path, token in studio.items()
        if path.startswith("motion.easing.")
    }
    for name in sorted(set(source_easings) | set(figma_easings)):
        source_token = source_easings.get(name)
        figma_token = figma_easings.get(name)
        if source_token is None or figma_token is None:
            report.fail(
                "drift",
                f"motion.easing.{name}",
                "declared in only one of tokens/motion.json and "
                f"{FIGMA_FILE}:motion.easing",
            )
            continue
        points = source_token.get("$value")
        css = str(studio_literal(figma_token, studio))
        match = CUBIC_BEZIER_CSS_RE.match(css)
        if match is None:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:motion.easing.{name}",
                f"is {css!r}, which is not a cubic-bezier() a prototype can enter",
            )
            continue
        figma_points = [float(group) for group in match.groups()]
        # Two different failures, reported separately, because they have
        # different culprits. A source $value that is not a four-number list is a
        # defect in tokens/motion.json; a list that disagrees with the Figma copy
        # is drift in the Figma copy. Collapsing them into one branch also put a
        # non-list on the wrong side of an `or`, so the diagnostic below it
        # iterated whatever the source held: a None crashed the validator and a
        # string produced a comma-separated list of its characters.
        if not isinstance(points, list):
            report.fail(
                "drift",
                f"motion.easing.{name}",
                f"$value is {points!r}, which is not the four-number list a "
                f"cubic-bezier needs, while {FIGMA_FILE} says {css}",
            )
            continue
        if [float(point) for point in points] != figma_points:
            report.fail(
                "drift",
                f"{FIGMA_FILE}:motion.easing.{name}",
                f"is {css} but the source is "
                f"cubic-bezier({', '.join(str(point) for point in points)})",
            )
        else:
            report.count("easings")


# ---------------------------------------------------------------------------
# Colour drift: tokens/ against the generated CSS custom properties
# ---------------------------------------------------------------------------

LIGHT_DARK_RE = re.compile(
    r"^light-dark\(\s*(#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?)\s*,\s*"
    r"(#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?)\s*\)$"
)
COLOUR_LITERAL_RE = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")

#: Marker a token group carries to say it is deliberately not exported to CSS.
EXPORT_MARKER = "com.viavitae.export"

#: Chart chrome is suffixed per theme in the source and grouped per theme in the
#: derived copies. The light entry assembles the pair; the dark one is consumed.
CHART_CHROME_LIGHT_RE = re.compile(r"^color\.chart\.(?:grid|axis|label)$")
CHART_CHROME_DARK_RE = re.compile(r"^color\.chart\.(?:grid|axis|label)-dark$")


def parse_css_colour(raw: str) -> tuple[str | None, str | None]:
    """Return ``(light, dark)`` for a CSS colour declaration value.

    Two forms are comparable: a bare literal, which is what the
    ``@supports not (color: light-dark())`` fallback and the ``@media print``
    override use, and a ``light-dark()`` pair, which is what ``:root`` uses. A
    value that is neither — a ``var()`` reference, a composed shadow — is not a
    colour this check can reason about and returns ``(None, None)``.

    A bare literal is returned as its own dark value: where both themes resolve
    to the same colour the CSS emits one literal rather than a redundant pair,
    and treating that as "light only, dark unknown" would report a false gap.
    """
    text = raw.strip()
    pair = LIGHT_DARK_RE.match(text)
    if pair is not None:
        return pair.group(1).upper(), pair.group(2).upper()
    if COLOUR_LITERAL_RE.match(text):
        return text.upper(), text.upper()
    return None, None


def collect_export_exclusions(repo_root: Path, report: Report) -> set[str]:
    """Return dotted-path prefixes whose tokens are deliberately not in the CSS.

    A group opts out with ``$extensions["com.viavitae.export"].css = false``, and
    the reason has to be written down in the same block. An omission that is
    documented and checked is a decision; an omission that is neither is a bug
    that looks like a decision until somebody needs the token.
    """
    excluded: set[str] = set()

    # Defined outside the loop and taking the file name as a parameter. Binding a
    # loop variable in a closure is the defect ruff's B023 exists to catch: the
    # closure captures the variable rather than its value, so every diagnostic
    # would name whichever file the loop finished on. The call below happens
    # inside the same iteration, so the behaviour is correct today — but a closure
    # that is correct only because of where it happens to be called is one
    # refactor away from silently blaming the wrong file, and blaming the wrong
    # file sends the next reader to edit a token that is not broken.
    def visit(node: Any, prefix: str, relative: str) -> None:
        if not isinstance(node, Mapping):
            return
        marker = node.get("$extensions", {})
        if isinstance(marker, Mapping):
            export = marker.get(EXPORT_MARKER)
            if isinstance(export, Mapping) and export.get("css") is False:
                description = export.get("$description")
                if not isinstance(description, str) or not description.strip():
                    report.fail(
                        "export",
                        f"{relative}:{prefix or '<root>'}",
                        f"{EXPORT_MARKER}.css is false but no $description says why; "
                        "a deliberate omission has to be a documented decision",
                    )
                if prefix:
                    excluded.add(prefix)
                return
        for key, child in node.items():
            if key.startswith("$") or key == BOOKKEEPING_KEY:
                continue
            visit(child, f"{prefix}.{key}" if prefix else key, relative)

    for relative in TOKEN_FILES:
        document = load_raw(repo_root, relative, report)
        if not isinstance(document, Mapping):
            continue
        visit(document, "", relative)
    return excluded


def css_property_for(source_path: str) -> str | None:
    """Return the CSS custom property that must carry ``source_path``, or ``None``.

    ``None`` means the token is not a colour the CSS exposes as its own property.
    The semantic tier is the one place where the source path and the property
    name differ by more than a prefix: ``color.semantic.light.surface.page`` and
    ``color.semantic.dark.surface.page`` collapse into a single
    ``--vv-color-surface-page`` holding a ``light-dark()`` pair, which is the
    whole reason the theme can be switched by an attribute instead of a rebuild.
    """
    match = re.match(r"^color\.palette\.([a-z]+)\.(\d+)$", source_path)
    if match:
        return f"--vv-color-{match.group(1)}-{match.group(2)}"

    match = re.match(
        r"^color\.semantic\.(?:light|dark)\.(surface|text|border|state)\.(.+)$",
        source_path,
    )
    if match:
        return f"--vv-color-{match.group(1)}-{match.group(2)}"

    match = re.match(r"^color\.chart\.(?:light|dark)\.(\d+)$", source_path)
    if match:
        return f"--vv-color-chart-{match.group(1)}"

    match = re.match(r"^color\.chart\.(grid|axis|label)(?:-dark)?$", source_path)
    if match:
        return f"--vv-color-chart-{match.group(1)}"

    match = re.match(r"^color\.church\.([a-z]+)\.(.+)$", source_path)
    if match:
        return f"--vv-church-{match.group(1)}-{match.group(2)}"

    match = re.match(r"^season\.([a-z]+)\.(.+)$", source_path)
    if match:
        return f"--vv-season-{match.group(1)}-{match.group(2)}"

    return None


def check_css_colour_drift(
    repo_root: Path, source: Mapping[str, str], report: Report
) -> None:
    """Compare every exported colour token against ``build/css/tokens.css``.

    Run in both directions, because the two directions catch different defects.
    Source to CSS catches a token that changed and a stylesheet that did not.
    CSS to source catches a hex value typed straight into the stylesheet, which
    is the more common failure and the one that survives review, since a reviewer
    reading a CSS diff has no way to know the literal in front of them was
    supposed to come from a token.
    """
    css = read_css(repo_root, TOKENS_CSS, report)
    if css is None:
        return
    properties = extract_custom_properties(css)
    excluded = collect_export_exclusions(repo_root, report)

    def is_excluded(path: str) -> bool:
        return any(
            path == prefix or path.startswith(prefix + ".") for prefix in excluded
        )

    expected: dict[str, tuple[str, str, str]] = {}
    for path, hex_value in sorted(source.items()):
        if is_excluded(path):
            continue
        if CHART_CHROME_DARK_RE.match(path):
            # Consumed by its light twin below, which assembles the pair.
            continue
        property_name = css_property_for(path)
        if property_name is None:
            continue
        # A dark-theme twin resolves to the same property as its light sibling,
        # so the pair is assembled once rather than written twice.
        light_path = path.replace(".dark.", ".light.")
        dark_path = path.replace(".light.", ".dark.")
        if CHART_CHROME_LIGHT_RE.match(path):
            light_path, dark_path = path, path + "-dark"
        series = re.match(r"^color\.chart\.light\.(\d+)$", path)
        if series:
            light_path, dark_path = path, "color.chart.dark." + series.group(1)
        light = source.get(light_path, hex_value)
        dark = source.get(dark_path, light)
        previous = expected.get(property_name)
        if previous is not None and previous[1:] != (light, dark):
            report.fail(
                "drift",
                f"{TOKENS_CSS}:{property_name}",
                f"{path} and {previous[0]} both claim this property but resolve "
                f"differently: {previous[1:]} against {(light, dark)}",
            )
        expected[property_name] = (path, light, dark)

    for property_name, (origin, light, dark) in sorted(expected.items()):
        wanted = light if light == dark else "light-dark(" + light + ", " + dark + ")"
        declared = properties.get(property_name)
        if not declared:
            report.fail(
                "drift",
                f"{TOKENS_CSS}:{property_name}",
                f"not declared, but {origin} resolves to {wanted}",
            )
            continue
        matched = False
        for raw in sorted(declared):
            css_light, css_dark = parse_css_colour(raw)
            if css_light is None:
                continue
            if css_light == light and css_dark == dark:
                matched = True
            elif css_light == light and raw.strip().startswith("#"):
                # A fallback or print block legitimately supplies the light value
                # alone; it is not a claim about the dark theme.
                matched = True
        if matched:
            report.count("css-colours")
        else:
            report.fail(
                "drift",
                f"{TOKENS_CSS}:{property_name}",
                f"declared as {', '.join(sorted(declared))} but {origin} resolves to {wanted}",
            )

    claimed = set(expected)
    for property_name in sorted(properties):
        if not property_name.startswith(
            ("--vv-color-", "--vv-church-", "--vv-season-")
        ):
            continue
        if property_name in claimed:
            continue
        literals = [
            raw for raw in properties[property_name] if parse_css_colour(raw)[0]
        ]
        if not literals:
            continue  # a var() indirection or a composed value, not a colour
        report.fail(
            "drift",
            f"{TOKENS_CSS}:{property_name}",
            f"carries {', '.join(sorted(literals))} but no token in tokens/ maps to "
            "it; a colour typed into the stylesheet cannot be themed, audited for "
            "contrast, or traced to a decision",
        )


# ---------------------------------------------------------------------------
# Reporting and entry point
# ---------------------------------------------------------------------------

#: Counter labels, in the order they are reported.
COUNT_LABELS: tuple[tuple[str, str], ...] = (
    ("files", "token files parsed"),
    ("structured", "token files structurally valid"),
    ("tokens", "tokens found"),
    ("typed", "literal values type-checked"),
    ("aliased", "aliases resolved and re-checked"),
    ("colours", "colours matched against the Figma copy"),
    ("css-colours", "colours matched against tokens.css"),
    ("breakpoints", "breakpoint copies matched"),
    ("queries", "media queries matched to a token"),
    ("containers", "container copies matched"),
    ("durations", "durations matched against the Figma copy"),
    ("easings", "easings matched against the Figma copy"),
)


def format_report(report: Report, verbose: bool) -> str:
    lines: list[str] = []
    lines.append("token validation")
    for key, label in COUNT_LABELS:
        if key in report.counts:
            lines.append(f"  {label:<46} {report.counts[key]}")
    if report.failures:
        lines.append("")
        lines.append(f"failures ({len(report.failures)})")
        for diagnostic in report.failures:
            lines.append("  " + diagnostic.render().replace("\n", "\n  "))
    elif verbose:
        lines.append("")
        lines.append("every check passed")
    if verbose and report.notes:
        lines.append("")
        lines.append("notes")
        for note in report.notes:
            lines.append(f"  - {note}")
    if not report.failures and not verbose:
        lines.append("The token set is structurally valid and no copy has drifted.")
    return "\n".join(lines)


def run(repo_root: Path, verbose: bool = False, as_json: bool = False) -> int:
    """Run every check and return a process exit code."""
    repo_root = repo_root.resolve()
    report = Report()

    for relative in TOKEN_FILES + (FIGMA_FILE, TOKENS_CSS, RESET_CSS):
        if not (repo_root / relative).is_file():
            report.fail("presence", relative, "file is missing")

    tokens = load_token_namespace(repo_root, report)
    check_structure(repo_root, report)
    check_bookkeeping(repo_root, report)
    if tokens:
        check_types(tokens, report)
        check_aliases(tokens, report)
        colours = collect_source_colours(tokens, report)
        check_colour_drift(repo_root, colours, report)
        check_css_colour_drift(repo_root, colours, report)
        check_breakpoint_drift(repo_root, tokens, report)
        check_motion_drift(repo_root, tokens, report)

    if as_json:
        print(
            json.dumps(
                {
                    "ok": report.ok,
                    "counts": report.counts,
                    "failures": [
                        {
                            "check": item.check,
                            "location": item.location,
                            "message": item.message,
                        }
                        for item in report.failures
                    ],
                    "notes": report.notes if verbose else [],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(format_report(report, verbose))

    return 0 if report.ok else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_tokens.py",
        description=(
            "Validate the ViaVitae design token set: DTCG structure, $type "
            "conformance, alias resolution, and drift between the token sources "
            "and their generated CSS and Figma copies."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root; defaults to the parent of this script's directory",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="report the counts and notes as well as the failures",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit JSON instead of a report",
    )
    arguments = parser.parse_args(argv)

    try:
        return run(arguments.repo_root, arguments.verbose, arguments.as_json)
    except TokenError as exc:
        print(f"validate_tokens: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":
    sys.exit(main())
