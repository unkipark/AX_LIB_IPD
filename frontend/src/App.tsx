import { useQuery } from '@tanstack/react-query'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { ApiError, api, setAuthMode } from '@/lib/api'
import { useTheme } from '@/lib/theme'
import { AdminUsersPage } from '@/pages/AdminUsersPage'
import { AgentPage } from '@/pages/AgentPage'
import { ArtifactDetailPage } from '@/pages/ArtifactDetailPage'
import { ArtifactFormPage } from '@/pages/ArtifactFormPage'
import { CatalogPage } from '@/pages/CatalogPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { LoginPage } from '@/pages/LoginPage'
import { ProfilePage } from '@/pages/ProfilePage'

export default function App() {
  const theme = useTheme()
  const onLoginPage = useLocation().pathname === '/login'
  const config = useQuery({ queryKey: ['authConfig'], queryFn: api.authConfig, staleTime: Infinity })
  // me 요청이 401 을 받기 전에 로그인 방식이 정해져 있어야 하므로 렌더 중에 바로 반영합니다.
  if (config.data) setAuthMode(config.data.mode)

  // /api/me 가 401 이면 api.ts 가 로그인 화면(또는 SSO)으로 보냅니다. 그 전까지는 빈 화면을 둡니다.
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, enabled: !!config.data && !onLoginPage })

  const error = config.error ?? me.error
  if (error && !(error instanceof ApiError && error.status === 401)) {
    return <p className="p-6 text-sm text-fail">서버에 연결하지 못했습니다. {(error as Error).message}</p>
  }
  if (!config.data) return null
  if (onLoginPage) return <LoginPage config={config.data} />
  if (!me.data) return null

  const user = me.data
  return (
    <Routes>
      <Route element={<Layout user={user} theme={theme} />}>
        <Route index element={<DashboardPage colors={theme.colors} />} />
        <Route path="artifacts" element={<CatalogPage />} />
        <Route path="artifacts/new" element={<ArtifactFormPage />} />
        <Route path="artifacts/:id" element={<ArtifactDetailPage />} />
        <Route path="artifacts/:id/edit" element={<ArtifactFormPage />} />
        <Route path="agent" element={<AgentPage />} />
        <Route path="agent/:conversationId" element={<AgentPage />} />
        <Route path="me" element={<ProfilePage user={user} config={config.data} />} />
        {user.role === 'admin' && <Route path="admin/users" element={<AdminUsersPage me={user} config={config.data} />} />}
        <Route path="*" element={<p className="text-sm text-inkMuted">페이지를 찾을 수 없습니다.</p>} />
      </Route>
    </Routes>
  )
}
