import { useQuery } from '@tanstack/react-query'
import { Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { ApiError, api } from '@/lib/api'
import { useTheme } from '@/lib/theme'
import { ArtifactDetailPage } from '@/pages/ArtifactDetailPage'
import { ArtifactFormPage } from '@/pages/ArtifactFormPage'
import { CatalogPage } from '@/pages/CatalogPage'
import { DashboardPage } from '@/pages/DashboardPage'

export default function App() {
  const theme = useTheme()
  // /api/me 가 401 이면 api.ts 가 SSO 로그인으로 보냅니다. 그 전까지는 빈 화면을 둡니다.
  const { data: user, error } = useQuery({ queryKey: ['me'], queryFn: api.me })

  if (error && !(error instanceof ApiError && error.status === 401)) {
    return <p className="p-6 text-sm text-fail">서버에 연결하지 못했습니다. {(error as Error).message}</p>
  }
  if (!user) return null

  return (
    <Routes>
      <Route element={<Layout user={user} theme={theme} />}>
        <Route index element={<DashboardPage colors={theme.colors} />} />
        <Route path="artifacts" element={<CatalogPage />} />
        <Route path="artifacts/new" element={<ArtifactFormPage />} />
        <Route path="artifacts/:id" element={<ArtifactDetailPage />} />
        <Route path="artifacts/:id/edit" element={<ArtifactFormPage />} />
        <Route path="*" element={<p className="text-sm text-inkMuted">페이지를 찾을 수 없습니다.</p>} />
      </Route>
    </Routes>
  )
}
