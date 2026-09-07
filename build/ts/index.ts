/**
 * ViaVitae design tokens for TypeScript consumers.
 *
 * Where `css/tokens.css` exposes tokens as custom properties that resolve at
 * runtime, this module exposes them as literal values that resolve at compile
 * time. Both are needed, and neither substitutes for the other:
 *
 *   - In a stylesheet or a JSX `className`, use the CSS custom properties or the
 *     Tailwind preset. Theming then works by an attribute on `<html>` with no
 *     rebuild.
 *   - In JavaScript that has to hand a colour to something that is not the DOM —
 *     a canvas, an SVG string, a chart library, a PDF generator, an OG-image
 *     renderer, a test assertion — use this module. `var(--vv-color-navy-900)`
 *     is meaningless to a canvas 2D context, and a chart library that receives
 *     it renders nothing.
 *
 * Every value here is the RESOLVED literal from `../tokens/*.json`. Aliases such
 * as `{color.palette.navy.900}` have already been followed, so a consumer never
 * has to. The consequence is that this file is a derived artefact: it is
 * regenerated from the token source by `../tools/build_exports.py` and must not
 * be hand-edited. A hand edit here is invisible to the CSS and Figma consumers
 * and therefore silently forks the system.
 *
 * @packageDocumentation
 */

/**
 * A CSS hex colour. The template literal type means a typo such as `#0E1B3` or
 * `0E1B3D` is a compile error rather than a runtime one that renders as
 * transparent black. Eight-digit form is permitted for alpha, which the overlay
 * and shadow tokens use.
 */
export type HexColor = `#${string}`;

/** A CSS length. Always carries its unit; a bare number is a compile error. */
export type CssLength = `${number}${"px" | "rem" | "em" | "ch" | "%"}`;

/** A CSS duration. */
export type CssDuration = `${number}ms`;

/** The two themes. */
export type Theme = "light" | "dark";

/** The four liturgical seasons. */
export type Season = "advent" | "lent" | "easter" | "ordinary";

/** The four church contexts a page can be about. */
export type ChurchContext = "funeral" | "cemetery" | "parish" | "basilica";

// ---------------------------------------------------------------------------
// Palette — raw ramps, fixed, theme-independent
// ---------------------------------------------------------------------------

/**
 * Brand navy. Anchor `#0E1B3D` at step 900. The structural colour: headers,
 * footers, dark surfaces, and primary text on a light background where it
 * measures 15.37:1 against ivory.
 */
export const navy = {
  50: "#F4F5F8",
  100: "#E6E9F1",
  200: "#C9D1E6",
  300: "#9CADDB",
  400: "#6181D3",
  500: "#2D56C3",
  600: "#224295",
  700: "#1B3374",
  800: "#142655",
  900: "#0E1B3D",
  950: "#091127",
} as const satisfies Record<number, HexColor>;

/**
 * Brand gold. Anchor `#C9A227` at step 500.
 *
 * Step 500 FAILS every text-contrast threshold on a light surface — 2.20:1
 * against ivory, 2.42:1 against white — and passes comfortably on navy at
 * 6.98:1. It is therefore decoration, iconography and text-on-dark only. For
 * gold that carries meaning as text on a light surface, use step 700.
 */
export const gold = {
  50: "#FDFBF4",
  100: "#FAF6E8",
  200: "#F5ECCE",
  300: "#F0E0B0",
  400: "#E8D187",
  500: "#C9A227",
  600: "#AB8A21",
  700: "#806719",
  800: "#604D13",
  900: "#44370D",
} as const satisfies Record<number, HexColor>;

/**
 * Brand ivory. Anchor `#F7F4EC` at step 100, the default page surface. White
 * cards sit on it, which gives a raised surface without a shadow.
 */
export const ivory = {
  50: "#FEFDFC",
  100: "#F7F4EC",
  200: "#F1EBDD",
  300: "#E8DFC7",
  400: "#DBCDA9",
  500: "#CAB681",
} as const satisfies Record<number, HexColor>;

/**
 * Interactive blue. Anchor `#2E6BFF` at step 500. Reserved for interactive
 * affordance and never used as decoration, because a colour reserved for
 * interaction is the only way a user learns to trust it.
 */
export const accent = {
  50: "#EDF2FF",
  100: "#D9E4FF",
  200: "#B0C7FF",
  300: "#789FFF",
  400: "#4E82FF",
  500: "#2E6BFF",
  600: "#0046F0",
  700: "#0039C2",
  800: "#002D99",
  900: "#002378",
} as const satisfies Record<number, HexColor>;

/**
 * Warm neutral, hue-matched to ivory so greys do not read as dirty against a
 * warm page. Carries UI chrome that is not brand.
 */
export const neutral = {
  50: "#FAFAFA",
  100: "#F4F4F3",
  200: "#E7E6E4",
  300: "#D6D4CF",
  400: "#B8B5AD",
  500: "#8A8578",
  600: "#7B766B",
  700: "#615D54",
  800: "#46433C",
  900: "#2E2D28",
} as const satisfies Record<number, HexColor>;

/** All palette ramps under one name. */
export const palette = { navy, gold, ivory, accent, neutral } as const;

// ---------------------------------------------------------------------------
// Semantic — theme-aware roles, resolved to literals per theme
// ---------------------------------------------------------------------------

/** The shape both themes share. Identical keys, different values. */
export interface SemanticColors {
  readonly surface: {
    readonly page: HexColor;
    readonly raised: HexColor;
    readonly sunken: HexColor;
    readonly overlay: HexColor;
    readonly inverse: HexColor;
  };
  readonly text: {
    readonly primary: HexColor;
    readonly secondary: HexColor;
    readonly muted: HexColor;
    readonly disabled: HexColor;
    readonly inverse: HexColor;
    readonly link: HexColor;
    readonly linkHover: HexColor;
    readonly linkRaised: HexColor;
    readonly linkVisited: HexColor;
    readonly brand: HexColor;
    readonly onGold: HexColor;
  };
  readonly border: {
    readonly default: HexColor;
    readonly strong: HexColor;
    readonly input: HexColor;
    readonly focus: HexColor;
    readonly divider: HexColor;
  };
  readonly state: {
    readonly success: HexColor;
    readonly successTint: HexColor;
    readonly warning: HexColor;
    readonly warningTint: HexColor;
    readonly danger: HexColor;
    readonly dangerTint: HexColor;
    readonly info: HexColor;
    readonly infoTint: HexColor;
  };
}

/** Light theme. Page surface ivory-100; cards white so they read as raised. */
export const semanticLight = {
  surface: {
    page: ivory[100],
    raised: "#FFFFFF",
    sunken: ivory[200],
    overlay: "#0E1B3DCC",
    inverse: navy[900],
  },
  text: {
    primary: navy[900],
    secondary: navy[700],
    muted: neutral[700],
    disabled: neutral[400],
    inverse: ivory[100],
    link: accent[600],
    linkHover: accent[700],
    linkRaised: accent[600],
    linkVisited: "#7D1F6E",
    brand: gold[700],
    onGold: navy[900],
  },
  border: {
    default: ivory[300],
    strong: ivory[400],
    input: neutral[500],
    focus: accent[500],
    divider: ivory[200],
  },
  state: {
    success: "#1F7A4C",
    successTint: "#E4F0E8",
    warning: "#995C00",
    warningTint: "#FBEEDA",
    danger: "#B3261E",
    dangerTint: "#F8E4E1",
    info: "#1B5E8A",
    infoTint: "#E3EDF4",
  },
} as const satisfies SemanticColors;

/**
 * Dark theme. Page surface navy-900.
 *
 * Two roles differ from a naive inversion of the light theme, and both exist
 * because of a measured contrast result rather than a preference. `text.brand`
 * is gold-500 rather than gold-700: on navy, brand gold IS text-safe at 6.98:1,
 * so the darker substitute the light theme needs would be a needless loss of
 * brand presence. `text.linkRaised` is accent-300 rather than accent-400:
 * accent-400 measures 4.80:1 on navy-900 but only 4.14:1 on the navy-800 raised
 * surface, so a link inside a dark card fails AA unless it steps up.
 */
export const semanticDark = {
  surface: {
    page: navy[900],
    raised: navy[800],
    sunken: navy[950],
    overlay: "#050A1ACC",
    inverse: ivory[100],
  },
  text: {
    primary: ivory[100],
    secondary: navy[200],
    muted: navy[300],
    disabled: navy[600],
    inverse: navy[900],
    link: accent[400],
    linkHover: accent[300],
    linkRaised: accent[300],
    linkVisited: "#F0C5E9",
    brand: gold[500],
    onGold: navy[900],
  },
  border: {
    default: navy[700],
    strong: navy[600],
    input: navy[400],
    focus: accent[400],
    divider: navy[800],
  },
  state: {
    success: "#5FD39A",
    successTint: "#123524",
    warning: "#E8B45C",
    warningTint: "#3A2C10",
    danger: "#F2836F",
    dangerTint: "#3D1512",
    info: "#7CC4E8",
    infoTint: "#10293A",
  },
} as const satisfies SemanticColors;

/** Resolve the semantic roles for a theme. */
export function semantic(theme: Theme): SemanticColors {
  return theme === "dark" ? semanticDark : semanticLight;
}

// ---------------------------------------------------------------------------
// Church contexts and liturgical seasons
// ---------------------------------------------------------------------------

/**
 * Church-context pairs: the colour roles a page ABOUT a context needs. Applied
 * per page, never per component.
 */
export const churchContexts = {
  /** Bereavement. Austerity: no gold, no saturated accent, no celebratory
   *  green. Text contrast is 17.04:1, the highest in the system, because the
   *  audience is frequently elderly and frequently distressed. */
  funeral: {
    surface: navy[950],
    surfaceRaised: navy[900],
    text: ivory[100],
    textMuted: navy[300],
    accent: navy[300],
    rule: navy[700],
  },
  /** Memorial garden. Stone and weathered bronze; pale surface for legibility
   *  in direct daylight. */
  cemetery: {
    surface: ivory[200],
    surfaceRaised: "#FFFFFF",
    text: navy[900],
    textMuted: neutral[700],
    accent: gold[700],
    rule: ivory[400],
  },
  /** Parish life: rotas, notices, giving. The default look of a parish page. */
  parish: {
    surface: ivory[100],
    surfaceRaised: "#FFFFFF",
    text: navy[900],
    textMuted: neutral[700],
    accent: gold[700],
    rule: ivory[300],
  },
  /** Heritage and the ceremonial register. Navy with gold, the inverse of
   *  parish. Gold is text-safe here at 6.98:1. */
  basilica: {
    surface: navy[900],
    surfaceRaised: navy[800],
    text: ivory[100],
    textMuted: navy[300],
    accent: gold[500],
    rule: gold[600],
  },
} as const satisfies Record<ChurchContext, Record<string, HexColor>>;

/**
 * Liturgical season themes, additive over the core identity. A season changes
 * the ceremonial surface, its soft companion and one accent; navy, gold, ivory
 * and the interactive accent stay exactly as the core tokens define them.
 *
 * Seasons are date- and rite-dependent and are resolved by the consuming
 * application from its own calendar. Nothing here encodes a date range.
 */
export const seasons = {
  advent: {
    surface: "#4A2C6D",
    surfaceSoft: "#EDE6F5",
    accent: gold[500],
    accentRose: "#9C4F66",
    textOnSurface: ivory[100],
    textMutedOnSurface: "#E8DFC7",
    textOnSoft: navy[900],
    rule: "#6B4E8C",
  },
  lent: {
    surface: "#3E2A55",
    surfaceSoft: "#EDEBE7",
    /** Ash. 5.37:1 on ivory, 4.96:1 on the soft surface, 5.90:1 for white
     *  labels on an ash fill. Only 2.13:1 against the violet surface, so ash
     *  is a foreground on a light ground; the dark surface takes `rule`. */
    accent: "#666460",
    accentRose: "#9C4F66",
    textOnSurface: ivory[100],
    textMutedOnSurface: "#E8DFC7",
    textOnSoft: navy[900],
    rule: "#5B4473",
    goldPermitted: gold[500],
  },
  easter: {
    surface: "#FFFFFF",
    surfaceSoft: "#FDFBF6",
    /** Decoration only on this surface: 2.42:1 against white. Use accentText
     *  for gold that carries meaning as text. */
    accent: gold[500],
    accentText: gold[700],
    textOnSurface: navy[900],
    textMutedOnSurface: neutral[700],
    textOnSoft: navy[900],
    rule: ivory[300],
    pentecost: "#A31621",
  },
  ordinary: {
    surface: "#1F5C3A",
    surfaceSoft: "#E4F0E8",
    /** 3.28:1 on green: clears the 3:1 non-text threshold, fails the 4.5:1
     *  text threshold. Use accentText for gold as text. */
    accent: gold[500],
    accentText: gold[400],
    textOnSurface: ivory[100],
    textMutedOnSurface: "#E8DFC7",
    textOnSoft: navy[900],
    rule: "#2E7A4E",
  },
} as const;

/**
 * The Paschal Triduum carries no theme. From the evening of Holy Thursday until
 * the Easter Vigil no season applies and a site falls back to the unthemed core
 * identity. Exposed as a value rather than left implicit so that a calendar
 * service can return it explicitly instead of defaulting to Lent by mistake.
 */
export const triduumAppliesTheme = false as const;

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------

/** Eight categorical series, ordered. */
export interface ChartRamp {
  readonly 1: HexColor;
  readonly 2: HexColor;
  readonly 3: HexColor;
  readonly 4: HexColor;
  readonly 5: HexColor;
  readonly 6: HexColor;
  readonly 7: HexColor;
  readonly 8: HexColor;
}

/**
 * Light-theme series, drawn on ivory-100.
 *
 * Ordered as a luminance staircase — dark, light, dark, light — so consecutive
 * series stay distinguishable in greyscale and under colour-vision deficiency.
 * Worst on-surface contrast 3.06:1; worst consecutive separation 2.28:1.
 */
export const chartLight = {
  1: "#142D7A",
  2: "#977813",
  3: "#0C4742",
  4: "#E84760",
  5: "#7D1F6E",
  6: "#709427",
  7: "#784317",
  8: "#738FAB",
} as const satisfies ChartRamp;

/** Dark-theme series, drawn on navy-900. Worst on-surface contrast 3.59:1;
 *  worst consecutive separation 2.47:1. */
export const chartDark = {
  1: "#ACBDF2",
  2: "#8D7011",
  3: "#37DED0",
  4: "#E63650",
  5: "#F0C5E9",
  6: "#6B8E26",
  7: "#F2D5BC",
  8: "#718DAA",
} as const satisfies ChartRamp;

/** Grid, axis and label colours per theme. */
export const chartChrome = {
  light: { grid: ivory[300], axis: neutral[600], label: neutral[700] },
  dark: { grid: navy[700], axis: navy[300], label: navy[200] },
} as const;

/**
 * Resolve the chart palette for a theme: eight series plus the chrome that goes
 * with them, so a chart cannot mix series from one theme with a gridline from
 * the other.
 */
export function chartSeries(theme: Theme): {
  readonly series: ChartRamp;
  readonly grid: HexColor;
  readonly axis: HexColor;
  readonly label: HexColor;
} {
  return theme === "dark"
    ? { series: chartDark, ...chartChrome.dark }
    : { series: chartLight, ...chartChrome.light };
}

/**
 * Hue alone never carries meaning. WCAG 1.4.1 requires that colour is not the
 * only visual means of conveying information, so a chart using this palette must
 * label its series directly or provide a monochrome alternative. Asserted here
 * as a constant so a consuming component can reference the requirement instead
 * of rediscovering it.
 */
export const chartRequiresDirectLabels = true as const;

/** Eight series maximum. Beyond eight the ramp restarts and the chart is wrong. */
export const chartMaxSeries = 8 as const;

// ---------------------------------------------------------------------------
// Typography
// ---------------------------------------------------------------------------

/** Font stacks as arrays, ready for `font-family: stack.join(", ")`. */
export const fontFamily = {
  display: ["Fraunces", "Iowan Old Style", "Palatino Linotype", "Palatino", "Georgia", "serif"],
  displayCyrillic: ["Noto Serif", "PT Serif", "Georgia", "serif"],
  ui: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
  mono: ["ui-monospace", "SFMono-Regular", "SF Mono", "Menlo", "Consolas", "Liberation Mono", "monospace"],
} as const satisfies Record<string, readonly string[]>;

/**
 * `displayCyrillic` is not a stylistic alternative. Fraunces does not declare
 * Cyrillic coverage, so a Russian heading set in `display` falls back glyph by
 * glyph and renders as two typefaces in one line. Apply it under `[lang="ru"]`.
 *
 * The coverage claim is verified against the actual font binaries by
 * `../tools/cyrillic_check.py` before a release. A font's documented coverage
 * and its shipped coverage are not always the same thing, and a subsetted WOFF2
 * can drop a block the upstream release has.
 */
export const fontFamilyForLocale = {
  lt: { display: fontFamily.display, ui: fontFamily.ui },
  en: { display: fontFamily.display, ui: fontFamily.ui },
  ru: { display: fontFamily.displayCyrillic, ui: fontFamily.ui },
} as const;

/** Permitted weights. A weight not listed here is not shipped. */
export const fontWeight = {
  light: 300,
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const satisfies Record<string, number>;

/** One entry of the type scale. */
export interface TypeRole {
  readonly fontFamily: readonly string[];
  readonly fontSize: CssLength;
  readonly fontWeight: number;
  readonly lineHeight: number;
  readonly letterSpacing: string;
  /** clamp() expression, where the role is fluid. Absent for fixed roles. */
  readonly fluid?: string;
  /** Fraunces optical-size axis setting, where the role is display type. */
  readonly opticalSize?: number;
}

/**
 * The complete type scale on a 1.25 (major third) ratio with a 16px root.
 * Display roles are Fraunces; UI roles are Inter. h4-h6 switch to Inter because
 * below 20px a serif's hairlines lose definition at typical screen densities and
 * the smaller headings are doing structural UI work rather than display work.
 */
export const typeScale = {
  "display-2xl": { fontFamily: fontFamily.display, fontSize: "4.5rem", fontWeight: 700, lineHeight: 1.05, letterSpacing: "-0.02em", fluid: "clamp(2.75rem, 1.4rem + 5.6vw, 4.5rem)", opticalSize: 144 },
  "display-xl": { fontFamily: fontFamily.display, fontSize: "3.75rem", fontWeight: 700, lineHeight: 1.08, letterSpacing: "-0.02em", fluid: "clamp(2.375rem, 1.4rem + 3.9vw, 3.75rem)", opticalSize: 120 },
  "display-lg": { fontFamily: fontFamily.display, fontSize: "3rem", fontWeight: 600, lineHeight: 1.1, letterSpacing: "-0.015em", fluid: "clamp(2rem, 1.3rem + 2.8vw, 3rem)", opticalSize: 96 },
  "display-md": { fontFamily: fontFamily.display, fontSize: "2.25rem", fontWeight: 600, lineHeight: 1.15, letterSpacing: "-0.01em", fluid: "clamp(1.75rem, 1.4rem + 1.4vw, 2.25rem)", opticalSize: 60 },
  "display-sm": { fontFamily: fontFamily.display, fontSize: "1.875rem", fontWeight: 600, lineHeight: 1.2, letterSpacing: "-0.01em", opticalSize: 48 },

  "heading-1": { fontFamily: fontFamily.display, fontSize: "2.25rem", fontWeight: 600, lineHeight: 1.2, letterSpacing: "-0.01em" },
  "heading-2": { fontFamily: fontFamily.display, fontSize: "1.875rem", fontWeight: 600, lineHeight: 1.25, letterSpacing: "-0.01em" },
  "heading-3": { fontFamily: fontFamily.display, fontSize: "1.5rem", fontWeight: 500, lineHeight: 1.3, letterSpacing: "-0.005em" },
  "heading-4": { fontFamily: fontFamily.ui, fontSize: "1.25rem", fontWeight: 600, lineHeight: 1.35, letterSpacing: "0em" },
  "heading-5": { fontFamily: fontFamily.ui, fontSize: "1.125rem", fontWeight: 600, lineHeight: 1.4, letterSpacing: "0em" },
  "heading-6": { fontFamily: fontFamily.ui, fontSize: "1rem", fontWeight: 600, lineHeight: 1.45, letterSpacing: "0.005em" },

  "body-xl": { fontFamily: fontFamily.ui, fontSize: "1.25rem", fontWeight: 400, lineHeight: 1.6, letterSpacing: "-0.005em" },
  "body-lg": { fontFamily: fontFamily.ui, fontSize: "1.125rem", fontWeight: 400, lineHeight: 1.65, letterSpacing: "0em" },
  "body-md": { fontFamily: fontFamily.ui, fontSize: "1rem", fontWeight: 400, lineHeight: 1.6, letterSpacing: "0em" },
  "body-sm": { fontFamily: fontFamily.ui, fontSize: "0.875rem", fontWeight: 400, lineHeight: 1.55, letterSpacing: "0.005em" },
  "body-strong": { fontFamily: fontFamily.ui, fontSize: "1rem", fontWeight: 600, lineHeight: 1.6, letterSpacing: "0em" },

  caption: { fontFamily: fontFamily.ui, fontSize: "0.75rem", fontWeight: 500, lineHeight: 1.45, letterSpacing: "0.01em" },
  overline: { fontFamily: fontFamily.ui, fontSize: "0.75rem", fontWeight: 600, lineHeight: 1.3, letterSpacing: "0.1em" },
  code: { fontFamily: fontFamily.mono, fontSize: "0.875rem", fontWeight: 400, lineHeight: 1.6, letterSpacing: "0em" },
  metric: { fontFamily: fontFamily.ui, fontSize: "2.25rem", fontWeight: 700, lineHeight: 1.1, letterSpacing: "-0.02em" },
  "button-lg": { fontFamily: fontFamily.ui, fontSize: "1.0625rem", fontWeight: 600, lineHeight: 1.2, letterSpacing: "0.005em" },
  "button-md": { fontFamily: fontFamily.ui, fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.2, letterSpacing: "0.005em" },
  nav: { fontFamily: fontFamily.ui, fontSize: "0.9375rem", fontWeight: 500, lineHeight: 1.2, letterSpacing: "0.01em" },
} as const satisfies Record<string, TypeRole>;

/** Every role name in the scale, as a union. */
export type TypeRoleName = keyof typeof typeScale;

/**
 * Line length, in characters. `optimal` is the target for prose, `max` is the
 * hard ceiling — beyond it the eye loses the line on return — and `min` is the
 * floor at which a two-column layout must collapse to one.
 */
export const measure = {
  optimal: "66ch",
  max: "75ch",
  min: "35ch",
  narrow: "45ch",
} as const satisfies Record<string, CssLength>;

/** 12px caption is the smallest text anywhere in the system. */
export const minimumFontSize = "0.75rem" as const satisfies CssLength;

// ---------------------------------------------------------------------------
// Spacing, radius, elevation
// ---------------------------------------------------------------------------

/** The 4pt scale, keyed by step. `spacing[4]` is 16px. */
export const spacing = {
  0: "0px",
  px: "1px",
  0.5: "2px",
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  6: "24px",
  8: "32px",
  10: "40px",
  12: "48px",
  16: "64px",
  20: "80px",
  24: "96px",
  32: "128px",
  40: "160px",
  48: "192px",
} as const satisfies Record<string | number, CssLength>;

/** Page gutters by breakpoint, and the container widths. */
export const layout = {
  gutter: { base: "16px", md: "24px", lg: "32px", xl: "48px" },
  containerMax: "1280px",
  containerProse: "720px",
  containerWide: "1536px",
  sectionGap: "64px",
  gridGap: "24px",
  stackGap: "16px",
} as const;

/** Border widths. Kept out of the spacing scale because they are not spacing. */
export const borderWidth = {
  hairline: "1px",
  medium: "2px",
  heavy: "4px",
} as const satisfies Record<string, CssLength>;

/** Corner radii. Close to square by design. */
export const radius = {
  none: "0px",
  xs: "2px",
  sm: "4px",
  md: "6px",
  lg: "8px",
  xl: "12px",
  pill: "9999px",
  circle: "50%",
} as const satisfies Record<string, CssLength>;

/**
 * Inner-radius rule: an element inside a rounded container with padding between
 * them takes `max(0, outer - padding)`. Getting this wrong leaves a visible gap
 * of background at every corner, which reads as sloppiness even to someone who
 * cannot name it.
 */
export function innerRadius(outerPx: number, paddingPx: number): number {
  return Math.max(0, outerPx - paddingPx);
}

/** One box-shadow layer. */
export interface ShadowLayer {
  readonly color: HexColor;
  readonly offsetX: CssLength;
  readonly offsetY: CssLength;
  readonly blur: CssLength;
  readonly spread: CssLength;
  readonly inset: boolean;
}

/** An elevation level: a light-theme stack and a dark-theme stack. */
export interface ElevationLevel {
  readonly level: number;
  readonly light: readonly ShadowLayer[];
  readonly dark: readonly ShadowLayer[];
  readonly lightSurface: HexColor;
  readonly darkSurface: HexColor;
  readonly lightBorder: HexColor | "none";
  readonly darkBorder: HexColor | "none";
}

/**
 * Elevation, declared per theme.
 *
 * A drop shadow is the wrong mechanism on navy: there is almost nothing left to
 * darken, so the shadow renders as nothing and the raised element appears to
 * float with no support. The dark-theme stack therefore leads with an inset
 * ivory hairline — the light catching the top edge, which is how a real object
 * reads in a dark room — and pairs every level with a surface step and a border
 * that survives forced-colours mode, where box-shadow is removed entirely.
 */
export const elevation = {
  none: {
    level: 0,
    light: [],
    dark: [],
    lightSurface: ivory[100],
    darkSurface: navy[900],
    lightBorder: "none",
    darkBorder: "none",
  },
  raised: {
    level: 1,
    light: [
      { color: "#0E1B3D0D", offsetX: "0px", offsetY: "1px", blur: "2px", spread: "0px", inset: false },
      { color: "#0E1B3D14", offsetX: "0px", offsetY: "2px", blur: "4px", spread: "0px", inset: false },
    ],
    dark: [
      { color: "#F7F4EC12", offsetX: "0px", offsetY: "1px", blur: "0px", spread: "0px", inset: true },
      { color: "#050A1A80", offsetX: "0px", offsetY: "4px", blur: "12px", spread: "0px", inset: false },
    ],
    lightSurface: "#FFFFFF",
    darkSurface: navy[800],
    lightBorder: ivory[300],
    darkBorder: navy[700],
  },
  overlay: {
    level: 2,
    light: [
      { color: "#0E1B3D14", offsetX: "0px", offsetY: "2px", blur: "4px", spread: "0px", inset: false },
      { color: "#0E1B3D1F", offsetX: "0px", offsetY: "8px", blur: "16px", spread: "0px", inset: false },
    ],
    dark: [
      { color: "#F7F4EC1A", offsetX: "0px", offsetY: "1px", blur: "0px", spread: "0px", inset: true },
      { color: "#050A1AB3", offsetX: "0px", offsetY: "8px", blur: "24px", spread: "0px", inset: false },
    ],
    lightSurface: "#FFFFFF",
    darkSurface: navy[800],
    lightBorder: ivory[300],
    darkBorder: navy[600],
  },
  modal: {
    level: 3,
    light: [
      { color: "#0E1B3D1F", offsetX: "0px", offsetY: "8px", blur: "16px", spread: "0px", inset: false },
      { color: "#0E1B3D33", offsetX: "0px", offsetY: "24px", blur: "48px", spread: "0px", inset: false },
    ],
    dark: [
      { color: "#F7F4EC1F", offsetX: "0px", offsetY: "1px", blur: "0px", spread: "0px", inset: true },
      { color: "#050A1AE6", offsetX: "0px", offsetY: "24px", blur: "64px", spread: "0px", inset: false },
    ],
    lightSurface: "#FFFFFF",
    darkSurface: navy[800],
    lightBorder: "none",
    darkBorder: navy[600],
  },
  toast: {
    level: 4,
    light: [
      { color: "#0E1B3D29", offsetX: "0px", offsetY: "4px", blur: "12px", spread: "0px", inset: false },
      { color: "#0E1B3D1F", offsetX: "0px", offsetY: "16px", blur: "32px", spread: "0px", inset: false },
    ],
    dark: [
      { color: "#F7F4EC24", offsetX: "0px", offsetY: "1px", blur: "0px", spread: "0px", inset: true },
      { color: "#050A1ACC", offsetX: "0px", offsetY: "12px", blur: "32px", spread: "0px", inset: false },
    ],
    lightSurface: "#FFFFFF",
    darkSurface: navy[800],
    lightBorder: ivory[300],
    darkBorder: navy[600],
  },
  pressed: {
    level: -1,
    light: [
      { color: "#0E1B3D14", offsetX: "0px", offsetY: "1px", blur: "2px", spread: "0px", inset: true },
    ],
    dark: [
      { color: "#050A1A99", offsetX: "0px", offsetY: "2px", blur: "4px", spread: "0px", inset: true },
    ],
    lightSurface: "#FFFFFF",
    darkSurface: navy[800],
    lightBorder: "none",
    darkBorder: "none",
  },
} as const satisfies Record<string, ElevationLevel>;

/** Render one elevation level as a CSS `box-shadow` value for a theme. */
export function boxShadow(level: keyof typeof elevation, theme: Theme): string {
  const layers = theme === "dark" ? elevation[level].dark : elevation[level].light;
  if (layers.length === 0) return "none";
  return layers
    .map((l) => `${l.inset ? "inset " : ""}${l.offsetX} ${l.offsetY} ${l.blur} ${l.spread} ${l.color}`)
    .join(", ");
}

// ---------------------------------------------------------------------------
// Motion
// ---------------------------------------------------------------------------

/** Durations. The useful band is 100-300ms; most of the system lives there. */
export const duration = {
  instant: "0ms",
  immediate: "80ms",
  fast: "120ms",
  base: "200ms",
  moderate: "320ms",
  slow: "480ms",
  deliberate: "720ms",
  ceremonial: "1200ms",
} as const satisfies Record<string, CssDuration>;

/**
 * Easing curves. None overshoots: a spring is a simulator-sickness trigger and
 * is rejected outright rather than merely disabled under reduced motion, so no
 * component can come to depend on it.
 */
export const easing = {
  standard: "cubic-bezier(0.4, 0, 0.2, 1)",
  emphasized: "cubic-bezier(0.2, 0, 0, 1)",
  decelerate: "cubic-bezier(0, 0, 0.2, 1)",
  accelerate: "cubic-bezier(0.4, 0, 1, 1)",
  /** Elapsed-time indicators only. Easing a progress bar misrepresents the
   *  remaining time. */
  linear: "cubic-bezier(0, 0, 1, 1)",
} as const;

/** Named transitions, so a component never assembles its own property list. */
export const transition = {
  color: { property: "color, background-color, border-color, fill, stroke", duration: duration.fast, timingFunction: easing.standard },
  interactive: { property: "color, background-color, border-color, box-shadow, transform", duration: duration.fast, timingFunction: easing.standard },
  expand: { property: "height, opacity", duration: duration.base, timingFunction: easing.standard },
  enter: { property: "opacity, transform", duration: duration.moderate, timingFunction: easing.decelerate },
  exit: { property: "opacity, transform", duration: duration.base, timingFunction: easing.accelerate },
  fade: { property: "opacity", duration: duration.base, timingFunction: easing.standard },
  reveal: { property: "opacity, transform, clip-path", duration: duration.ceremonial, timingFunction: easing.emphasized },
  progress: { property: "width", duration: duration.base, timingFunction: easing.linear },
} as const;

/** Render a named transition as a CSS `transition` value. */
export function cssTransition(name: keyof typeof transition): string {
  const t = transition[name];
  return `${t.property} ${t.duration} ${t.timingFunction}`;
}

/**
 * The reduced-motion override set. Mandatory, not progressive: vestibular
 * dysfunction is common in adults over forty, which overlaps heavily with the
 * demographic that reads a parish website.
 *
 * Duration is 1ms rather than 0ms because a zero-length transition never fires
 * `transitionend`, which leaves a component stuck in its pre-transition state.
 */
export const reducedMotion = {
  mediaQuery: "(prefers-reduced-motion: reduce)",
  duration: "1ms" as const satisfies CssDuration,
  delay: "0ms" as const satisfies CssDuration,
  easing: easing.linear,
  iterationCount: 1,
  scrollBehavior: "auto",
  transform: "none",
  /** Removed outright — shortening them does not remove the effect that causes
   *  the problem. */
  disabled: ["parallax", "scroll-triggered reveal", "ken-burns zoom", "marquee and auto-advancing carousel", "staggered entrance"],
  /** Retained, collapsing to an instant state change, because they carry
   *  information rather than decoration. */
  retained: ["focus ring appearance", "progress advancement", "pending indicator", "disclosure expand"],
} as const;

// ---------------------------------------------------------------------------
// Breakpoints and icons
// ---------------------------------------------------------------------------

/** Viewport breakpoints. Identical to Tailwind's own defaults. */
export const breakpoint = {
  xs: "0px",
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
  xxl: "1536px",
} as const satisfies Record<string, CssLength>;

/** Build a mobile-first min-width media query. `xs` returns an empty string,
 *  because the base is the absence of a query rather than a query at 0px. */
export function minWidthQuery(name: keyof typeof breakpoint): string {
  return name === "xs" ? "" : `(min-width: ${breakpoint[name]})`;
}

/** Adaptive capability queries — a different question from viewport width. */
export const capabilityQuery = {
  touch: "(pointer: coarse) and (hover: none)",
  finePointer: "(pointer: fine) and (hover: hover)",
  anyHover: "(any-hover: hover)",
  darkScheme: "(prefers-color-scheme: dark)",
  lightScheme: "(prefers-color-scheme: light)",
  reducedMotion: "(prefers-reduced-motion: reduce)",
  moreContrast: "(prefers-contrast: more)",
  forcedColors: "(forced-colors: active)",
  reducedTransparency: "(prefers-reduced-transparency: reduce)",
  portrait: "(orientation: portrait)",
  landscape: "(orientation: landscape)",
  shortViewport: "(max-height: 500px)",
} as const;

/** Container-query sizes. */
export const containerQuerySize = {
  xs: "240px",
  sm: "384px",
  md: "448px",
  lg: "576px",
  xl: "768px",
} as const satisfies Record<string, CssLength>;

/** The narrowest viewport that must render without horizontal scrolling.
 *  A failure here is a WCAG 1.4.10 Reflow failure. */
export const minimumViewportWidth = "320px" as const satisfies CssLength;

/** One rendered icon size and the stroke weight that size actually needs. */
export interface IconSize {
  readonly size: CssLength;
  readonly strokeWidth: CssLength;
  readonly padding: CssLength;
}

/**
 * A keyline spanning two independent axes: an envelope, a screen, a phone. A
 * two-axis keyline is an object rather than a "WxH" string, because a string
 * that has to be split before use is a string every consumer splits slightly
 * differently.
 */
export interface KeylineBox {
  readonly width: CssLength;
  readonly height: CssLength;
}

/**
 * A keyline with one parameter: a square's side, a circle's diameter, or the
 * side of the square bounding box a diagonal glyph is drawn inside.
 */
export type KeylineScalar = CssLength;

/** The six keyline classes an icon is fitted to inside the 20px live area. */
export interface KeylineSet {
  readonly square: KeylineScalar;
  readonly circle: KeylineScalar;
  readonly landscape: KeylineBox;
  readonly portrait: KeylineBox;
  readonly diagonal: KeylineScalar;
  /** Not a measurement. The class an authoring tool tags a glyph with when no
   *  bounding box applies, so a geometry linter knows to skip the box check and
   *  the optical review becomes the only gate. */
  readonly irregular: "fit to 20px optical mass";
}

/**
 * Icon sizes. Stroke weight is NOT proportional to size: a 1.5px stroke scaled
 * to 16px renders at 1px, lands between device pixels, and antialiases into a
 * grey blur. Each size therefore declares the stroke it needs.
 */
export const icon = {
  grid: { size: "24px", liveArea: "20px", padding: "2px", strokeBase: "1.5px", strokeCap: "round", strokeJoin: "round" },
  size: {
    xs: { size: "16px", strokeWidth: "1.75px", padding: "0px" },
    sm: { size: "20px", strokeWidth: "1.75px", padding: "0px" },
    md: { size: "24px", strokeWidth: "1.5px", padding: "0px" },
    lg: { size: "32px", strokeWidth: "1.5px", padding: "4px" },
    xl: { size: "48px", strokeWidth: "1.25px", padding: "8px" },
  },
  /**
   * Keyline classes inside the 20px live area. A circle of 20px diameter and a
   * square of 20px side do not appear the same size, because the circle has no
   * corners reaching the bounding box, so each silhouette class is drawn to its
   * own keyline. `irregular` — a flame, a dove, the ichthys — carries no
   * measurement: it is the tag that tells a geometry linter the optical review
   * is the only gate for that glyph.
   */
  keyline: {
    square: "18px",
    circle: "20px",
    landscape: { width: "20px", height: "16px" },
    portrait: { width: "16px", height: "20px" },
    diagonal: "19px",
    irregular: "fit to 20px optical mass",
  },
  clearSpace: { minimum: "4px", toText: "8px", toIcon: "12px", toEdge: "12px" },
  /** WCAG 1.4.11: a graphical object needed to understand the content must
   *  clear 3:1 against adjacent colours. */
  minimumContrast: 3.0,
  /** 44px for anything primary; 24px is the absolute AA floor. */
  touchTargetMinimum: "44px",
  touchTargetFloor: "24px",
} as const satisfies { size: Record<string, IconSize>; keyline: KeylineSet } & Record<
  string,
  unknown
>;

/** Icon colour roles, resolved per theme. */
export function iconColors(theme: Theme): {
  readonly default: HexColor;
  readonly muted: HexColor;
  readonly interactive: HexColor;
  readonly onGold: HexColor;
} {
  const s = semantic(theme);
  return {
    default: s.text.secondary,
    muted: s.text.muted,
    interactive: s.text.link,
    onGold: s.text.onGold,
  };
}

// ---------------------------------------------------------------------------
// Contrast contract
// ---------------------------------------------------------------------------

/** One verified foreground/background pair. */
export interface ContrastPair {
  readonly foreground: HexColor;
  readonly background: HexColor;
  readonly minimum: number;
  /** The WCAG success criterion the minimum comes from. */
  readonly sc: string;
  readonly note?: string;
}

/**
 * The contrast contract, as data, mirroring the `$extensions` block in
 * `../tokens/colors.json`.
 *
 * `../tools/contrast_check.py` is the authority: it recomputes every ratio from
 * the token source and fails the build on any pair below its minimum. This list
 * exists so that a TypeScript consumer — a swatch renderer, a design-system
 * documentation site, a storybook addon — can show the verified ratio next to a
 * colour without reimplementing the WCAG arithmetic or trusting a hard-coded
 * number that the tokens have since moved away from.
 */
export const contrastPairs = {
  light: [
    { foreground: navy[900], background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: navy[900], background: "#FFFFFF", minimum: 4.5, sc: "1.4.3" },
    { foreground: navy[700], background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: neutral[700], background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: accent[600], background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: accent[700], background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#7D1F6E", background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: gold[700], background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: gold[700], background: "#FFFFFF", minimum: 4.5, sc: "1.4.3" },
    { foreground: navy[900], background: gold[500], minimum: 4.5, sc: "1.4.3" },
    { foreground: ivory[100], background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#1F7A4C", background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#995C00", background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#B3261E", background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#1B5E8A", background: ivory[100], minimum: 4.5, sc: "1.4.3" },
    { foreground: accent[500], background: ivory[100], minimum: 3.0, sc: "2.4.11" },
    { foreground: neutral[500], background: ivory[100], minimum: 3.0, sc: "1.4.11" },
  ],
  dark: [
    { foreground: ivory[100], background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: ivory[100], background: navy[800], minimum: 4.5, sc: "1.4.3" },
    { foreground: navy[200], background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: navy[300], background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: accent[400], background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: accent[300], background: navy[800], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#F0C5E9", background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: gold[500], background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: gold[500], background: navy[800], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#5FD39A", background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#E8B45C", background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#F2836F", background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: "#7CC4E8", background: navy[900], minimum: 4.5, sc: "1.4.3" },
    { foreground: accent[400], background: navy[900], minimum: 3.0, sc: "2.4.11" },
    { foreground: navy[400], background: navy[900], minimum: 3.0, sc: "1.4.11" },
  ],
} as const satisfies Record<Theme, readonly ContrastPair[]>;

/**
 * Combinations that look right and fail. A reviewer or a tool can reject these
 * by name rather than relying on someone remembering the arithmetic. The first
 * is the single most likely contrast regression in the system, because gold is
 * the colour a designer reaches for first.
 */
export const prohibitedPairs = [
  { foreground: gold[500], background: ivory[100], ratio: 2.2, reason: "Brand gold fails AA, AA-large and the 3:1 non-text threshold on ivory." },
  { foreground: gold[500], background: "#FFFFFF", ratio: 2.42, reason: "As above on a white card." },
  { foreground: "#FFFFFF", background: gold[500], ratio: 2.42, reason: "White text on a gold fill fails. A gold button carries navy-900 text." },
  { foreground: accent[500], background: ivory[100], ratio: 4.1, reason: "Below 4.5:1. Permitted for a focus ring, an icon or 24px display type; body link text uses accent-600." },
  { foreground: accent[400], background: navy[800], ratio: 4.14, reason: "A link inside a dark card fails AA. Use text.linkRaised (accent-300)." },
  { foreground: navy[900], background: navy[800], ratio: 1.16, reason: "Navy on navy. Dark-theme elevation is a surface step plus a hairline edge, never a text-colour change." },
  { foreground: neutral[400], background: ivory[100], ratio: 1.86, reason: "Disabled grey. Exempt as an inactive component under 1.4.3; the exemption does not extend to a required field's placeholder." },
] as const;

/**
 * WCAG 2.x relative luminance of a hex colour.
 *
 * Exposed because a consumer that generates a colour at runtime — a
 * data-visualisation library picking a series colour, an OG-image renderer
 * choosing a label colour — must be able to check its own output rather than
 * trusting a palette that does not contain the value it just invented.
 */
export function relativeLuminance(color: HexColor): number {
  const hex = color.replace("#", "");
  if (hex.length !== 6 && hex.length !== 8) {
    throw new RangeError(`Expected a 6- or 8-digit hex colour, received "${color}"`);
  }
  const channel = (offset: number): number => {
    const c = Number.parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * channel(0) + 0.7152 * channel(2) + 0.0722 * channel(4);
}

/**
 * WCAG 2.x contrast ratio between two colours, from 1 to 21.
 *
 * Alpha is ignored: the ratio of a translucent colour depends on what is behind
 * it, which this function cannot know. Composite the colour against its
 * intended background first and pass the opaque result.
 */
export function contrastRatio(a: HexColor, b: HexColor): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

/** WCAG 2.2 text-contrast thresholds. */
export const contrastThreshold = {
  /** SC 1.4.3, AA, body text. */
  aaBody: 4.5,
  /** SC 1.4.3, AA, large text: 24px, or 18.66px bold. */
  aaLarge: 3.0,
  /** SC 1.4.6, AAA, body text. */
  aaaBody: 7.0,
  /** SC 1.4.11, non-text contrast: UI components and graphical objects. */
  nonText: 3.0,
  /** SC 2.4.11, focus appearance: a 2 CSS pixel thick perimeter. */
  focusAppearance: 3.0,
} as const;

/**
 * Check a pair against a threshold and report the result. Returns the ratio as
 * well as the verdict, because "fails at 4.42 against a 4.5 minimum" is a
 * different conversation from "fails at 1.9" and a boolean alone hides it.
 */
export function checkContrast(
  foreground: HexColor,
  background: HexColor,
  minimum: number,
): { readonly passes: boolean; readonly ratio: number; readonly minimum: number } {
  const ratio = contrastRatio(foreground, background);
  return { passes: ratio >= minimum, ratio, minimum };
}

// ---------------------------------------------------------------------------
// CSS custom property names
// ---------------------------------------------------------------------------

/** Namespaces `cssVar` can resolve. */
type CssVarNamespace = "palette" | "role" | "season" | "context";

/**
 * Map a token reference to its CSS custom property name.
 *
 * Not a blind string transform: the CSS uses flattened names for the ACTIVE
 * theme's roles (`--vv-color-text-primary`), not for every theme's
 * (`--vv-color-semantic-light-text-primary`), so the mapping has to know which
 * namespace it is in. Passing a path outside the four known namespaces throws
 * rather than returning a property name that resolves to nothing — a silent
 * `var()` with no declaration behind it renders as the inherited value, which
 * is a much harder defect to find than an exception.
 *
 * @param namespace - which token family the path belongs to
 * @param path - dot-separated path within that namespace
 *
 * @example
 * ```ts
 * cssVar("palette", "navy.900");        // "--vv-color-navy-900"
 * cssVar("role", "text.primary");       // "--vv-color-text-primary"
 * cssVar("season", "advent.surface");   // "--vv-season-advent-surface"
 * cssVar("context", "funeral.text");    // "--vv-church-funeral-text"
 * ```
 */
export function cssVar(namespace: CssVarNamespace, path: string): string {
  if (path.length === 0) {
    throw new RangeError("cssVar requires a non-empty token path");
  }
  const segments = path.split(".").join("-");
  switch (namespace) {
    case "palette":
      return `--vv-color-${segments}`;
    case "role":
      return `--vv-color-${segments}`;
    case "season":
      return `--vv-season-${segments}`;
    case "context":
      return `--vv-church-${segments}`;
    default: {
      // Unreachable given the CssVarNamespace union. Present so that widening
      // the union without widening this function is a compile error here rather
      // than a `var()` that silently resolves to nothing at runtime.
      const exhausted: never = namespace;
      throw new RangeError(`cssVar received an unknown namespace: ${String(exhausted)}`);
    }
  }
}

/**
 * The attributes a consumer sets on `<html>` to select a theme and a season.
 * Declared here rather than left to convention so that a server renderer, a
 * theme provider and a CSS selector cannot disagree about the spelling.
 */
export const themeAttributes = {
  theme: { name: "data-theme", values: ["light", "dark"] },
  season: { name: "data-season", values: ["advent", "lent", "easter", "ordinary"] },
  context: { name: "data-context", values: ["funeral", "cemetery", "parish", "basilica"] },
} as const;

/** Everything, under one default export, for consumers that prefer it. */
export const tokens = {
  palette,
  semanticLight,
  semanticDark,
  churchContexts,
  seasons,
  chartLight,
  chartDark,
  chartChrome,
  fontFamily,
  fontFamilyForLocale,
  fontWeight,
  typeScale,
  measure,
  spacing,
  layout,
  borderWidth,
  radius,
  elevation,
  duration,
  easing,
  transition,
  reducedMotion,
  breakpoint,
  capabilityQuery,
  containerQuerySize,
  icon,
  contrastPairs,
  prohibitedPairs,
  contrastThreshold,
  themeAttributes,
} as const;

export default tokens;
