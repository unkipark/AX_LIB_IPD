/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: v('c-canvas'),
        panel: v('c-panel'),
        panelRaised: v('c-panel-raised'),
        line: v('c-line'),
        ink: v('c-ink'),
        inkMuted: v('c-ink-muted'),
        series2: v('c-series2'),
        series1: v('c-series1'),
        accent: v('c-accent'),
        running: v('c-running'),
        ok: v('c-ok'),
        fail: v('c-fail'),
      },
      fontFamily: {
        sans: ['"IBM Plex Sans Variable"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: { panel: '3px' },
    },
  },
  plugins: [],
}
