import { useCallback, useEffect, useState } from 'react'

/** UI 크롬 테마 — 배경·패널·글자색. */
export const THEMES = [
  { id: 'dark', label: '다크' },
  { id: 'light', label: '라이트' },
  { id: 'contrast', label: '고대비' },
  { id: 'claude-light', label: 'Claude 라이트' },
  { id: 'claude-dark', label: 'Claude 다크' },
] as const

/** 데이터·의미 색 — 차트 시리즈와 상태 배지. */
export const PALETTES = [
  { id: 'okabe', label: 'Okabe–Ito', hint: '전 색각 유형 검증' },
  { id: 'tol', label: 'Tol 고대비', hint: '3색 · 흑백 출력 대응' },
  { id: 'claude', label: 'Claude', hint: '파랑·주황 축' },
] as const

export type ThemeId = (typeof THEMES)[number]['id']
export type PaletteId = (typeof PALETTES)[number]['id']

const THEME_KEY = 'axlib.theme'
const PALETTE_KEY = 'axlib.palette'

function readStored<T extends string>(key: string, allowed: readonly { id: string }[], fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    if (v && allowed.some((a) => a.id === v)) return v as T
  } catch {
    // 브라우저가 스토리지를 막아둔 환경 — 기본값으로 진행합니다.
  }
  return fallback
}

/** 현재 테마의 토큰을 실제 rgb() 문자열로 읽어옵니다.
 *  Recharts 는 CSS 변수를 직접 못 받으므로 계산된 값이 필요합니다. */
export type ThemeColors = Record<
  'canvas' | 'panel' | 'panelRaised' | 'line' | 'ink' | 'inkMuted' | 'grid' | 'accent' | 'series1' | 'series2' | 'running' | 'ok' | 'fail',
  string
>

const VAR_MAP: Record<keyof ThemeColors, string> = {
  canvas: '--c-canvas', panel: '--c-panel', panelRaised: '--c-panel-raised',
  line: '--c-line', ink: '--c-ink', inkMuted: '--c-ink-muted', grid: '--c-grid',
  accent: '--c-accent', series1: '--c-series1', series2: '--c-series2',
  running: '--c-running', ok: '--c-ok', fail: '--c-fail',
}

function readColors(): ThemeColors {
  const style = getComputedStyle(document.documentElement)
  const out = {} as ThemeColors
  for (const [key, cssVar] of Object.entries(VAR_MAP)) {
    const channels = style.getPropertyValue(cssVar).trim()
    out[key as keyof ThemeColors] = channels ? `rgb(${channels})` : 'transparent'
  }
  return out
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeId>(() => readStored(THEME_KEY, THEMES, 'dark'))
  const [palette, setPaletteState] = useState<PaletteId>(() => readStored(PALETTE_KEY, PALETTES, 'okabe'))
  const [colors, setColors] = useState<ThemeColors>(() => ({} as ThemeColors))

  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = theme
    root.dataset.palette = palette
    // 변수 적용 후 한 프레임 뒤에 읽어야 새 값이 나옵니다.
    const id = requestAnimationFrame(() => setColors(readColors()))
    return () => cancelAnimationFrame(id)
  }, [theme, palette])

  const setTheme = useCallback((id: ThemeId) => {
    setThemeState(id)
    try { localStorage.setItem(THEME_KEY, id) } catch { /* 무시 */ }
  }, [])

  const setPalette = useCallback((id: PaletteId) => {
    setPaletteState(id)
    try { localStorage.setItem(PALETTE_KEY, id) } catch { /* 무시 */ }
  }, [])

  return { theme, setTheme, palette, setPalette, colors }
}
