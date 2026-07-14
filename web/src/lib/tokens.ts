// Verasettle visual system: calm ivory, charcoal ink, and one accountable teal.
// Teal Ink (not bright teal) is used for text on light surfaces for WCAG AA.

export const C = {
  bg: {
    base: '#F3F4F1', // ivory canvas
    surface: '#FFFFFF', // pure surface
    elevated: '#F4F6F3', // mist surface
  },
  border: {
    hairline: '#EEF0EC',
    strong: '#E6E8E4',
  },
  text: {
    ghost: '#8A94A2', // metadata
    muted: '#5B6776', // secondary copy
    secondary: '#334155', // values, metadata
    primary: '#0E1620', // charcoal ink
  },
  // Semantic. Colour never carries meaning alone — every chip also carries a word.
  state: {
    approved: '#059669',
    rejected: '#C2413A',
    vetoed: '#A16207',
    held: '#0D9488',
    hypothetical: '#0E3A53',
    broken: '#C2413A',
  },
} as const

export const MONO = "'JetBrains Mono', 'Geist Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
export const SANS = "Geist, 'Avenir Next', ui-sans-serif, system-ui, sans-serif"

/** 4px base unit. */
export const S = (n: number) => `${n * 4}px`
