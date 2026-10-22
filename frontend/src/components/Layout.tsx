import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router-dom'
import { Library, LogOut, Plus } from 'lucide-react'
import { ThemeSelector } from '@/components/ThemeSelector'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import type { useTheme } from '@/lib/theme'
import { cn } from '@/lib/utils'
import type { User } from '@/types'

const NAV = [
  { to: '/', label: '현황판', end: true },
  { to: '/artifacts', label: '산출물', end: false },
]

export function Layout({ user, theme }: { user: User; theme: ReturnType<typeof useTheme> }) {
  const agent = useQuery({ queryKey: ['agentStatus'], queryFn: api.agentStatus, staleTime: 60_000 })
  const nav = [
    ...NAV,
    ...(agent.data?.enabled ? [{ to: '/agent', label: 'AI 도우미', end: false }] : []),
    ...(user.role === 'admin' ? [{ to: '/admin/users', label: '사용자 관리', end: false }] : []),
  ]
  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-10 flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-panel px-4 py-2.5">
        <NavLink to="/" className="flex items-center gap-2">
          <Library className="size-4 text-accent" aria-hidden />
          <h1 className="text-sm font-medium">AX 산출물 라이브러리</h1>
        </NavLink>

        <Separator orientation="vertical" className="h-5" />

        <nav className="flex items-center gap-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                cn(
                  'rounded-panel px-2.5 py-1 text-xs font-medium transition-colors',
                  isActive ? 'bg-panelRaised text-ink' : 'text-inkMuted hover:text-ink'
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <Button asChild size="sm">
          <NavLink to="/artifacts/new">
            <Plus /> 산출물 등록
          </NavLink>
        </Button>

        <div className="ml-auto flex items-center gap-3">
          <ThemeSelector
            theme={theme.theme}
            palette={theme.palette}
            onTheme={theme.setTheme}
            onPalette={theme.setPalette}
          />
          <NavLink to="/me" className="rounded-panel px-1.5 py-1 text-xs text-inkMuted hover:bg-panelRaised" title="내 정보">
            <span className="text-ink">{user.name}</span>
            {user.department && <span> · {user.department}</span>}
            {user.role === 'admin' && <span className="ml-1 text-accent">(관리자)</span>}
          </NavLink>
          <Button asChild variant="ghost" size="icon" title="로그아웃">
            <a href="/api/auth/logout" aria-label="로그아웃">
              <LogOut />
            </a>
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 p-4">
        <Outlet />
      </main>
    </div>
  )
}
