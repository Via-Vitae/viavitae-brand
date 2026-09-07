/**
 * ViaVitae brand preset for Tailwind CSS v4.
 *
 * THE web consumption entry point. Every colour, font, spacing, radius, shadow,
 * duration and breakpoint in the system is exposed here as a Tailwind theme
 * value, so a consumer writes `bg-navy-900 text-ivory-100 rounded-sm` and gets
 * the brand rather than an approximation of it.
 *
 * HOW THIS IS CONSUMED
 *
 * Tailwind v4 is CSS-first: the canonical way to extend a theme is an `@theme`
 * block in your stylesheet. v4 still supports a JavaScript/TypeScript config
 * through the `@config` directive, which is what this file targets.
 *
 *   /* app.css *\/
 *   @import "tailwindcss";
 *   @config "../node_modules/@viavitae/brand/tailwind.preset.ts";
 *
 *   /* tailwind.config.ts (v3-style, or v4 via @config) *\/
 *   import brand from "@viavitae/brand/tailwind-preset";
 *   export default { presets: [brand], content: ["./app/**\/*.tsx"] };
 *
 * If you prefer the CSS-first path with no JavaScript config at all, import
 * `@viavitae/brand/tokens.css` and write your own `@theme` block referencing
 * the custom properties — they carry exactly the same values. See
 * ../examples/tailwind-static/index.html.
 *
 * WHY VALUES ARE CSS CUSTOM PROPERTIES
 *
 * Every colour below resolves to `var(--vv-...)` rather than to a literal hex
 * value. That is deliberate and it is the whole reason the dark theme and the
 * liturgical season themes work at all: Tailwind emits one utility class, and
 * the value it resolves to changes with the `data-theme` and `data-season`
 * attributes on `<html>`. A literal hex in this file would be compiled into the
 * class at build time, so a theme switch would require a rebuild rather than an
 * attribute change.
 *
 * The custom properties themselves are declared in css/tokens.css, which must
 * be loaded. Loading this preset without tokens.css produces utilities that
 * resolve to `var(--vv-...)` with no declaration behind them, and every
 * branded element falls back to the inherited or initial value. tokens.css is
 * not optional.
 *
 * GENERATED FILE
 *
 * Derived from ../tokens/*.json by ../tools/build_exports.py. Do not hand-edit:
 * the next regeneration overwrites the change, and a value that exists here but
 * not in the token source is a value no other consumer can see.
 *
 * @packageDocumentation
 */

/**
 * A colour value Tailwind accepts. Either a literal CSS colour or a reference
 * to a custom property. Every brand value is the latter, so that theming is a
 * runtime attribute change rather than a build-time constant.
 */
type ColorValue = string;

/**
 * A nested colour group: any depth of named groups resolving to colour values.
 * Recursive, because Tailwind accepts arbitrary nesting and the brand palette
 * uses three levels (`season.advent.surface`). Declared as an interface rather
 * than a type alias so the self-reference is unambiguously legal.
 */
interface ColorGroup {
  readonly [key: string]: ColorValue | ColorGroup;
}

/**
 * A `fontSize` entry: the size, plus the line-height, letter-spacing and
 * font-weight that belong to it. Tailwind applies all four when the utility is
 * used, which is what stops a consumer setting `text-body-md` and then
 * hand-coding a line-height that disagrees with the scale.
 */
type FontSizeValue = readonly [
  size: string,
  options: {
    readonly lineHeight: string;
    readonly letterSpacing: string;
    readonly fontWeight: string;
  },
];

/** A box-shadow entry, or a pair of entries for a themed surface. */
type ShadowValue = string;

/**
 * The structural shape of the object this module exports.
 *
 * Declared locally rather than imported from `tailwindcss` so that this file
 * typechecks with no dependency installed. `tailwindcss` is an optional peer
 * dependency of the package: a consumer using the CSS-first path never installs
 * it, and a typecheck that failed without it would make the package unusable on
 * exactly the path the tokens exist to support.
 *
 * The shape is a subset of Tailwind's own `Config['theme']` and is assignable to
 * it. If Tailwind's theme contract changes in a way this subset no longer
 * satisfies, the failure surfaces in the consumer's typecheck, not silently at
 * runtime.
 */
export interface BrandTailwindPreset {
  readonly theme: {
    readonly extend: {
      readonly colors: Readonly<Record<string, ColorValue | ColorGroup>>;
      readonly fontFamily: Readonly<Record<string, readonly string[]>>;
      readonly fontSize: Readonly<Record<string, FontSizeValue>>;
      readonly spacing: Readonly<Record<string, string>>;
      readonly borderRadius: Readonly<Record<string, string>>;
      readonly boxShadow: Readonly<Record<string, ShadowValue>>;
      readonly transitionDuration: Readonly<Record<string, string>>;
      readonly transitionTimingFunction: Readonly<Record<string, string>>;
      readonly screens: Readonly<Record<string, string>>;
      readonly containers: Readonly<Record<string, string>>;
      readonly maxWidth: Readonly<Record<string, string>>;
      readonly letterSpacing: Readonly<Record<string, string>>;
      readonly lineHeight: Readonly<Record<string, string>>;
      readonly fontWeight: Readonly<Record<string, string>>;
      readonly zIndex: Readonly<Record<string, string>>;
    };
  };
}

/**
 * Colour ramps and semantic roles.
 *
 * Two tiers are exposed, and the distinction matters at the call site. The ramp
 * names (`navy-900`, `gold-500`) are raw palette steps: they do not change with
 * the theme, and using one in a component is how a light-theme colour ends up
 * hard-coded onto a dark surface. The role names (`surface-page`, `text-primary`,
 * `border-focus`) are semantic and DO change with the theme.
 *
 * Application code should use the role names. The ramp names are exposed for the
 * rare case that genuinely needs a fixed value regardless of theme — a logo
 * asset, a chart series, a print stylesheet — and their presence here is not an
 * invitation to reach for them.
 */
const colors = {
  // --- Palette ramps: fixed, theme-independent ------------------------------
  navy: {
    50: "var(--vv-color-navy-50)",
    100: "var(--vv-color-navy-100)",
    200: "var(--vv-color-navy-200)",
    300: "var(--vv-color-navy-300)",
    400: "var(--vv-color-navy-400)",
    500: "var(--vv-color-navy-500)",
    600: "var(--vv-color-navy-600)",
    700: "var(--vv-color-navy-700)",
    800: "var(--vv-color-navy-800)",
    900: "var(--vv-color-navy-900)",
    950: "var(--vv-color-navy-950)",
  },
  gold: {
    50: "var(--vv-color-gold-50)",
    100: "var(--vv-color-gold-100)",
    200: "var(--vv-color-gold-200)",
    300: "var(--vv-color-gold-300)",
    400: "var(--vv-color-gold-400)",
    500: "var(--vv-color-gold-500)",
    600: "var(--vv-color-gold-600)",
    700: "var(--vv-color-gold-700)",
    800: "var(--vv-color-gold-800)",
    900: "var(--vv-color-gold-900)",
  },
  ivory: {
    50: "var(--vv-color-ivory-50)",
    100: "var(--vv-color-ivory-100)",
    200: "var(--vv-color-ivory-200)",
    300: "var(--vv-color-ivory-300)",
    400: "var(--vv-color-ivory-400)",
    500: "var(--vv-color-ivory-500)",
  },
  accent: {
    50: "var(--vv-color-accent-50)",
    100: "var(--vv-color-accent-100)",
    200: "var(--vv-color-accent-200)",
    300: "var(--vv-color-accent-300)",
    400: "var(--vv-color-accent-400)",
    500: "var(--vv-color-accent-500)",
    600: "var(--vv-color-accent-600)",
    700: "var(--vv-color-accent-700)",
    800: "var(--vv-color-accent-800)",
    900: "var(--vv-color-accent-900)",
  },
  neutral: {
    50: "var(--vv-color-neutral-50)",
    100: "var(--vv-color-neutral-100)",
    200: "var(--vv-color-neutral-200)",
    300: "var(--vv-color-neutral-300)",
    400: "var(--vv-color-neutral-400)",
    500: "var(--vv-color-neutral-500)",
    600: "var(--vv-color-neutral-600)",
    700: "var(--vv-color-neutral-700)",
    800: "var(--vv-color-neutral-800)",
    900: "var(--vv-color-neutral-900)",
  },

  // --- Semantic roles: change with data-theme ------------------------------
  surface: {
    page: "var(--vv-color-surface-page)",
    raised: "var(--vv-color-surface-raised)",
    sunken: "var(--vv-color-surface-sunken)",
    overlay: "var(--vv-color-surface-overlay)",
    inverse: "var(--vv-color-surface-inverse)",
  },
  text: {
    primary: "var(--vv-color-text-primary)",
    secondary: "var(--vv-color-text-secondary)",
    muted: "var(--vv-color-text-muted)",
    disabled: "var(--vv-color-text-disabled)",
    inverse: "var(--vv-color-text-inverse)",
    link: "var(--vv-color-text-link)",
    "link-hover": "var(--vv-color-text-link-hover)",
    "link-raised": "var(--vv-color-text-link-raised)",
    "link-visited": "var(--vv-color-text-link-visited)",
    brand: "var(--vv-color-text-brand)",
    "on-gold": "var(--vv-color-text-on-gold)",
  },
  border: {
    DEFAULT: "var(--vv-color-border-default)",
    strong: "var(--vv-color-border-strong)",
    input: "var(--vv-color-border-input)",
    focus: "var(--vv-color-border-focus)",
    divider: "var(--vv-color-border-divider)",
  },
  state: {
    success: "var(--vv-color-state-success)",
    "success-tint": "var(--vv-color-state-success-tint)",
    warning: "var(--vv-color-state-warning)",
    "warning-tint": "var(--vv-color-state-warning-tint)",
    danger: "var(--vv-color-state-danger)",
    "danger-tint": "var(--vv-color-state-danger-tint)",
    info: "var(--vv-color-state-info)",
    "info-tint": "var(--vv-color-state-info-tint)",
  },

  /**
   * Chart series, indexed 1-8. Ordered so consecutive series are separated by
   * at least 2.28:1 in relative luminance and every series clears 3:1 against
   * its surface. Hue alone must never carry meaning: label the series directly
   * or ship a monochrome alternative, per WCAG 1.4.1.
   */
  chart: {
    1: "var(--vv-color-chart-1)",
    2: "var(--vv-color-chart-2)",
    3: "var(--vv-color-chart-3)",
    4: "var(--vv-color-chart-4)",
    5: "var(--vv-color-chart-5)",
    6: "var(--vv-color-chart-6)",
    7: "var(--vv-color-chart-7)",
    8: "var(--vv-color-chart-8)",
    grid: "var(--vv-color-chart-grid)",
    axis: "var(--vv-color-chart-axis)",
    label: "var(--vv-color-chart-label)",
  },

  /**
   * Liturgical season colours. These do NOT change with data-theme; they change
   * with data-season, and each season declares its own surface, soft surface and
   * accent. A season is applied to a page, never to a component, because two
   * adjacent components in different seasons on one page is not a design.
   */
  season: {
    advent: {
      surface: "var(--vv-season-advent-surface)",
      soft: "var(--vv-season-advent-surface-soft)",
      accent: "var(--vv-season-advent-accent)",
      rose: "var(--vv-season-advent-accent-rose)",
      text: "var(--vv-season-advent-text-on-surface)",
    },
    lent: {
      surface: "var(--vv-season-lent-surface)",
      soft: "var(--vv-season-lent-surface-soft)",
      accent: "var(--vv-season-lent-accent)",
      rose: "var(--vv-season-lent-accent-rose)",
      text: "var(--vv-season-lent-text-on-surface)",
    },
    easter: {
      surface: "var(--vv-season-easter-surface)",
      soft: "var(--vv-season-easter-surface-soft)",
      accent: "var(--vv-season-easter-accent)",
      text: "var(--vv-season-easter-text-on-surface)",
      pentecost: "var(--vv-season-easter-pentecost)",
    },
    ordinary: {
      surface: "var(--vv-season-ordinary-surface)",
      soft: "var(--vv-season-ordinary-surface-soft)",
      accent: "var(--vv-season-ordinary-accent)",
      text: "var(--vv-season-ordinary-text-on-surface)",
    },
  },
} as const satisfies BrandTailwindPreset["theme"]["extend"]["colors"];

/**
 * Font stacks. `display-cyrillic` is the Russian display face and is not a
 * stylistic alternative: Fraunces does not declare Cyrillic coverage, so a
 * Russian heading set in `display` falls back glyph by glyph and renders as two
 * different typefaces in one line. The locale rules in css/tokens.css apply
 * `display-cyrillic` automatically under [lang="ru"].
 */
const fontFamily = {
  display: [
    "Fraunces",
    "Iowan Old Style",
    "Palatino Linotype",
    "Palatino",
    "Georgia",
    "serif",
  ],
  "display-cyrillic": ["Noto Serif", "PT Serif", "Georgia", "serif"],
  ui: [
    "Inter",
    "system-ui",
    "-apple-system",
    "Segoe UI",
    "Roboto",
    "Helvetica Neue",
    "Arial",
    "sans-serif",
  ],
  mono: [
    "ui-monospace",
    "SFMono-Regular",
    "SF Mono",
    "Menlo",
    "Consolas",
    "Liberation Mono",
    "monospace",
  ],
} as const satisfies BrandTailwindPreset["theme"]["extend"]["fontFamily"];

/**
 * The type scale. Each entry carries its line-height, letter-spacing and
 * font-weight so a single utility produces a complete, correct typographic
 * role. `fluid-*` entries use clamp() and interpolate between the sm and xl
 * breakpoints; the fixed entries are the scale's fallback for a consumer that
 * cannot or will not use clamp().
 */
const fontSize = {
  "display-2xl": ["4.5rem", { lineHeight: "1.05", letterSpacing: "-0.02em", fontWeight: "700" }],
  "display-xl": ["3.75rem", { lineHeight: "1.08", letterSpacing: "-0.02em", fontWeight: "700" }],
  "display-lg": ["3rem", { lineHeight: "1.1", letterSpacing: "-0.015em", fontWeight: "600" }],
  "display-md": ["2.25rem", { lineHeight: "1.15", letterSpacing: "-0.01em", fontWeight: "600" }],
  "display-sm": ["1.875rem", { lineHeight: "1.2", letterSpacing: "-0.01em", fontWeight: "600" }],

  "heading-1": ["2.25rem", { lineHeight: "1.2", letterSpacing: "-0.01em", fontWeight: "600" }],
  "heading-2": ["1.875rem", { lineHeight: "1.25", letterSpacing: "-0.01em", fontWeight: "600" }],
  "heading-3": ["1.5rem", { lineHeight: "1.3", letterSpacing: "-0.005em", fontWeight: "500" }],
  "heading-4": ["1.25rem", { lineHeight: "1.35", letterSpacing: "0em", fontWeight: "600" }],
  "heading-5": ["1.125rem", { lineHeight: "1.4", letterSpacing: "0em", fontWeight: "600" }],
  "heading-6": ["1rem", { lineHeight: "1.45", letterSpacing: "0.005em", fontWeight: "600" }],

  "body-xl": ["1.25rem", { lineHeight: "1.6", letterSpacing: "-0.005em", fontWeight: "400" }],
  "body-lg": ["1.125rem", { lineHeight: "1.65", letterSpacing: "0em", fontWeight: "400" }],
  "body-md": ["1rem", { lineHeight: "1.6", letterSpacing: "0em", fontWeight: "400" }],
  "body-sm": ["0.875rem", { lineHeight: "1.55", letterSpacing: "0.005em", fontWeight: "400" }],
  "body-strong": ["1rem", { lineHeight: "1.6", letterSpacing: "0em", fontWeight: "600" }],

  caption: ["0.75rem", { lineHeight: "1.45", letterSpacing: "0.01em", fontWeight: "500" }],
  overline: ["0.75rem", { lineHeight: "1.3", letterSpacing: "0.1em", fontWeight: "600" }],
  code: ["0.875rem", { lineHeight: "1.6", letterSpacing: "0em", fontWeight: "400" }],
  metric: ["2.25rem", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "700" }],
  "button-lg": ["1.0625rem", { lineHeight: "1.2", letterSpacing: "0.005em", fontWeight: "600" }],
  "button-md": ["0.9375rem", { lineHeight: "1.2", letterSpacing: "0.005em", fontWeight: "600" }],
  nav: ["0.9375rem", { lineHeight: "1.2", letterSpacing: "0.01em", fontWeight: "500" }],

  // Fluid variants, clamp()-based, interpolating sm -> xl.
  "fluid-display-2xl": [
    "clamp(2.75rem, 1.4rem + 5.6vw, 4.5rem)",
    { lineHeight: "1.05", letterSpacing: "-0.02em", fontWeight: "700" },
  ],
  "fluid-display-xl": [
    "clamp(2.375rem, 1.4rem + 3.9vw, 3.75rem)",
    { lineHeight: "1.08", letterSpacing: "-0.02em", fontWeight: "700" },
  ],
  "fluid-display-lg": [
    "clamp(2rem, 1.3rem + 2.8vw, 3rem)",
    { lineHeight: "1.1", letterSpacing: "-0.015em", fontWeight: "600" },
  ],
  "fluid-display-md": [
    "clamp(1.75rem, 1.4rem + 1.4vw, 2.25rem)",
    { lineHeight: "1.15", letterSpacing: "-0.01em", fontWeight: "600" },
  ],
  "fluid-heading-1": [
    "clamp(1.75rem, 1.4rem + 1.4vw, 2.25rem)",
    { lineHeight: "1.2", letterSpacing: "-0.01em", fontWeight: "600" },
  ],
} as const satisfies BrandTailwindPreset["theme"]["extend"]["fontSize"];

/**
 * The 4pt spacing scale. Keyed by scale step, so `p-4` is 16px and `gap-6` is
 * 24px, matching the token names in ../tokens/spacing.json.
 *
 * These EXTEND Tailwind's own spacing scale rather than replacing it. The
 * default scale is already 4px-based (Tailwind's `spacing` multiplier is
 * 0.25rem), so `p-4` resolves to the same 16px whether it comes from this preset
 * or from Tailwind itself — which is exactly why extending is safe here and
 * replacing would break every consumer's existing muscle memory.
 */
const spacing = {
  "0.5": "2px",
  "4.5": "18px",
  "13": "52px",
  "18": "72px",
  "22": "88px",
  "26": "104px",
  "30": "120px",
  "34": "136px",
  "42": "168px",
  "50": "200px",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["spacing"];

/** Corner radii. Close to square by design; see ../tokens/radius.json. */
const borderRadius = {
  none: "0px",
  xs: "2px",
  sm: "4px",
  md: "6px",
  lg: "8px",
  xl: "12px",
  pill: "9999px",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["borderRadius"];

/**
 * Elevation.
 *
 * Each utility resolves to a single composed custom property rather than to a
 * list of per-layer colour variables, because the two themes do not differ only
 * in colour: the dark stack leads with an `inset` hairline highlight and the
 * light stack does not, and `inset` is not something a colour variable can
 * express. Composing per level keeps the whole stack — order, inset flags and
 * colours — switchable by one `light-dark()` declaration in css/tokens.css.
 *
 * The consequence is that `shadow-raised` does the right thing on both themes
 * without the component knowing which theme it is in. A drop shadow is the wrong
 * elevation mechanism on navy — there is almost nothing left to darken — so the
 * dark stack substitutes a surface step plus a hairline top edge, which is how a
 * real object reads in a dark room.
 */
const boxShadow = {
  none: "var(--vv-elevation-none)",
  raised: "var(--vv-elevation-raised)",
  overlay: "var(--vv-elevation-overlay)",
  modal: "var(--vv-elevation-modal)",
  toast: "var(--vv-elevation-toast)",
  pressed: "var(--vv-elevation-pressed)",
  /** Focus ring: 2px at the accent colour plus a 2px offset. WCAG 2.2 SC 2.4.11
   *  requires a 2 CSS pixel thick perimeter, so a 1px ring fails regardless of
   *  how strong its contrast is. */
  "focus-ring": "0 0 0 2px var(--vv-color-surface-page), 0 0 0 4px var(--vv-color-border-focus)",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["boxShadow"];

/**
 * Transition durations. `base` at 200ms is the default; anything above 480ms
 * must be interruptible and must have a reduced-motion override, both of which
 * css/reset.css already provides.
 */
const transitionDuration = {
  instant: "0ms",
  immediate: "80ms",
  fast: "120ms",
  base: "200ms",
  moderate: "320ms",
  slow: "480ms",
  deliberate: "720ms",
  ceremonial: "1200ms",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["transitionDuration"];

/**
 * Easing curves. `standard` for a state change, `decelerate` for something
 * arriving, `accelerate` for something leaving, `linear` only for an
 * elapsed-time indicator. No curve here overshoots: a spring is a
 * simulator-sickness trigger and is rejected outright, see
 * ../tokens/motion.json.
 */
const transitionTimingFunction = {
  standard: "cubic-bezier(0.4, 0, 0.2, 1)",
  emphasized: "cubic-bezier(0.2, 0, 0, 1)",
  decelerate: "cubic-bezier(0, 0, 0.2, 1)",
  accelerate: "cubic-bezier(0.4, 0, 1, 1)",
  linear: "cubic-bezier(0, 0, 1, 1)",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["transitionTimingFunction"];

/**
 * Viewport breakpoints. Identical to Tailwind's own defaults, so `sm:`, `md:`,
 * `lg:`, `xl:` and `2xl:` behave the same with or without this preset. `xs` is
 * the base and is not a query; it is declared at 0px so that a consumer who
 * writes `xs:` gets a valid utility rather than a silent no-op.
 */
const screens = {
  xs: "0px",
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
  "2xl": "1536px",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["screens"];

/** Container-query sizes, for `@container` and `@[size]:` utilities. */
const containers = {
  xs: "240px",
  sm: "384px",
  md: "448px",
  lg: "576px",
  xl: "768px",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["containers"];

/**
 * Content measure widths. `prose` is the reading column: 720px puts body-lg at
 * 18px near the 66ch optimal measure declared in ../tokens/typography.json.
 * Exceeding it is the most common cause of an unreadable long-form page.
 */
const maxWidth = {
  prose: "720px",
  content: "1280px",
  wide: "1536px",
  "measure-optimal": "66ch",
  "measure-max": "75ch",
  "measure-min": "35ch",
  "measure-narrow": "45ch",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["maxWidth"];

/** Tracking values used by the scale, exposed for one-off adjustments. */
const letterSpacing = {
  "display-tight": "-0.02em",
  "heading-tight": "-0.01em",
  "heading-slight": "-0.005em",
  body: "0em",
  "body-loose": "0.005em",
  caption: "0.01em",
  overline: "0.1em",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["letterSpacing"];

/** Line-heights used by the scale. */
const lineHeight = {
  display: "1.05",
  "display-tight": "1.1",
  "display-loose": "1.2",
  heading: "1.3",
  "heading-loose": "1.45",
  body: "1.6",
  "body-loose": "1.65",
  "body-tight": "1.55",
  caption: "1.45",
  overline: "1.3",
  none: "1.2",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["lineHeight"];

/** Permitted font weights. A weight not listed here is not shipped. */
const fontWeight = {
  light: "300",
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["fontWeight"];

/**
 * Layer order. Declared once so that a modal is always above a toast that is
 * always above a dropdown, instead of each component picking a number and the
 * highest one winning by accident. The scale is sparse on purpose: gaps leave
 * room for a new layer without renumbering the ones above it.
 */
const zIndex = {
  base: "0",
  raised: "10",
  sticky: "100",
  dropdown: "500",
  overlay: "800",
  modal: "1000",
  toast: "1200",
  tooltip: "1400",
  "skip-link": "9999",
} as const satisfies BrandTailwindPreset["theme"]["extend"]["zIndex"];

/**
 * The preset. Spread into `presets: [...]` in a Tailwind config, or referenced
 * from a Tailwind v4 stylesheet with `@config`.
 */
export const brandPreset = {
  theme: {
    extend: {
      colors,
      fontFamily,
      fontSize,
      spacing,
      borderRadius,
      boxShadow,
      transitionDuration,
      transitionTimingFunction,
      screens,
      containers,
      maxWidth,
      letterSpacing,
      lineHeight,
      fontWeight,
      zIndex,
    },
  },
} as const satisfies BrandTailwindPreset;

export default brandPreset;
