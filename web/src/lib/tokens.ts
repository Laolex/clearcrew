// Design tokens. Every text token below clears WCAG AA (4.5:1) on `bg.base`;
// the ratio is stated so it can be re-checked rather than trusted.

export const C = {
  bg: {
    base: '#0E1110', // page
    surface: '#161A18', // raised panel
    elevated: '#1C2220', // hover, selected
  },
  border: {
    hairline: '#252B28',
    strong: '#343D39',
  },
  text: {
    ghost: '#757F7A', //  4.59:1 — index column, section labels
    muted: '#7A8580', //  4.97:1 — timestamps, labels
    secondary: '#B5BEB9', //  9.97:1 — values, metadata
    primary: '#E8EDEA', // 16.03:1 — prose, agent reasons
  },
  // Semantic. Colour never carries meaning alone — every chip also carries a word.
  state: {
    approved: '#52C47A',
    rejected: '#E0574F',
    vetoed: '#D9A441',
    held: '#5A9BD8',
    hypothetical: '#A78BC4',
    broken: '#E0574F',
  },
} as const

// IBM Plex — the typeface the rest of ClearCrew already uses.
export const MONO = "'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
export const SANS = "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif"

/** 4px base unit. */
export const S = (n: number) => `${n * 4}px`
