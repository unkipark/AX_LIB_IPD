import { Palette } from 'lucide-react'
import { PALETTES, THEMES, type PaletteId, type ThemeId } from '@/lib/theme'

interface Props {
  theme: ThemeId
  palette: PaletteId
  onTheme: (id: ThemeId) => void
  onPalette: (id: PaletteId) => void
}

const selectClass =
  'h-7 rounded-panel border border-line bg-panelRaised px-2 text-xs text-ink'

/** 크롬 테마와 데이터 팔레트를 따로 고릅니다.
 *  두 축이 독립이라 조합이 늘어도 관리할 토큰은 두 벌뿐입니다. */
export function ThemeSelector({ theme, palette, onTheme, onPalette }: Props) {
  return (
    <div className="flex items-center gap-1.5">
      <Palette className="size-4 text-inkMuted" aria-hidden />
      <select
        aria-label="화면 테마"
        value={theme}
        onChange={(e) => onTheme(e.target.value as ThemeId)}
        className={selectClass}
      >
        {THEMES.map((t) => (
          <option key={t.id} value={t.id}>{t.label}</option>
        ))}
      </select>
      <select
        aria-label="데이터 색상"
        value={palette}
        onChange={(e) => onPalette(e.target.value as PaletteId)}
        className={selectClass}
        title="차트와 상태 배지에 쓰이는 색"
      >
        {PALETTES.map((p) => (
          <option key={p.id} value={p.id}>{p.label}</option>
        ))}
      </select>
    </div>
  )
}
