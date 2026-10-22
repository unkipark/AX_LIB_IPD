import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, UserPlus, X } from 'lucide-react'
import { AccountFields, EMPTY_ACCOUNT, toSignupInput, type AccountDraft } from '@/components/AccountFields'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Select } from '@/components/ui/input'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/utils'
import type { AdminUser, AuthConfig, User } from '@/types'

export function AdminUsersPage({ me, config }: { me: User; config: AuthConfig }) {
  const qc = useQueryClient()
  const local = config.mode === 'local'
  const { data: users = [], error } = useQuery({ queryKey: ['adminUsers'], queryFn: api.adminUsers })
  const [filter, setFilter] = useState('')
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null)
  const [creating, setCreating] = useState(false)
  const [account, setAccount] = useState<AccountDraft>(EMPTY_ACCOUNT)

  const fail = (e: Error) => setNotice({ ok: false, text: e.message })
  const refresh = () => qc.invalidateQueries({ queryKey: ['adminUsers'] })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Pick<AdminUser, 'role' | 'isActive'>> }) =>
      api.adminUpdateUser(id, body),
    onSuccess: refresh,
    onError: fail,
  })
  const reset = useMutation({
    mutationFn: (u: AdminUser) => api.adminResetPassword(u.id).then((r) => ({ u, ...r })),
    onSuccess: ({ u, tempPassword }) =>
      setNotice({
        ok: true,
        text: `${u.name}(${u.loginId}) 임시 비밀번호: ${tempPassword}  — 본인에게 전달하고, 로그인 후 '내 정보'에서 바꾸도록 안내하세요.`,
      }),
    onError: fail,
  })
  const create = useMutation({
    mutationFn: api.adminCreateUser,
    onSuccess: (u) => {
      setNotice({ ok: true, text: `${u.name}(${u.loginId}) 계정을 만들었습니다.` })
      setAccount(EMPTY_ACCOUNT)
      setCreating(false)
      refresh()
    },
    onError: fail,
  })

  const q = filter.trim().toLowerCase()
  const rows = q
    ? users.filter((u) => [u.name, u.loginId, u.department].some((v) => v?.toLowerCase().includes(q)))
    : users

  if (error) return <p className="text-sm text-fail">{(error as Error).message}</p>

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">사용자 관리</h2>
        <span className="text-xs text-inkMuted">{users.length}명</span>
        <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="이름·사번·부서 검색"
          className="ml-auto w-56" aria-label="사용자 검색" />
        {local && (
          <Button size="sm" variant={creating ? 'outline' : 'default'} onClick={() => setCreating((v) => !v)}>
            {creating ? <><X /> 닫기</> : <><UserPlus /> 계정 만들기</>}
          </Button>
        )}
      </div>

      {notice && (
        <div className={`flex items-start gap-2 rounded-panel border px-3 py-2 text-xs ${
          notice.ok ? 'border-ok/40 bg-ok/10 text-ink' : 'border-fail/40 bg-fail/10 text-fail'}`}>
          <span className="flex-1 whitespace-pre-wrap font-mono">{notice.text}</span>
          <button onClick={() => setNotice(null)} aria-label="닫기"><X className="size-3.5" /></button>
        </div>
      )}

      {creating && (
        <Card>
          <CardHeader><CardTitle>새 계정</CardTitle></CardHeader>
          <CardContent>
            <form
              className="grid gap-3 sm:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault()
                const body = toSignupInput(account)
                if (typeof body === 'string') return setNotice({ ok: false, text: body })
                create.mutate(body)
              }}
            >
              <AccountFields value={account} onChange={setAccount} departments={config.departments} />
              <Button type="submit" className="sm:col-span-2 sm:justify-self-end" disabled={create.isPending}>
                <UserPlus /> 만들기
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <Card className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-line text-left text-inkMuted">
              <th className="px-3 py-2 font-medium">이름</th>
              <th className="px-3 py-2 font-medium">사번</th>
              <th className="px-3 py-2 font-medium">부서</th>
              <th className="px-3 py-2 text-right font-medium">산출물</th>
              <th className="px-3 py-2 font-medium">최근 로그인</th>
              <th className="px-3 py-2 font-medium">권한</th>
              <th className="px-3 py-2 font-medium">상태</th>
              {local && <th className="px-3 py-2 font-medium">비밀번호</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => {
              const self = u.id === me.id
              return (
                <tr key={u.id} className={`border-b border-line/50 ${u.isActive ? '' : 'opacity-50'}`}>
                  <td className="px-3 py-1.5 text-ink">{u.name}{self && <span className="ml-1 text-inkMuted">(나)</span>}</td>
                  <td className="px-3 py-1.5 font-mono">{u.loginId ?? u.empNo ?? '—'}</td>
                  <td className="px-3 py-1.5">{u.department ?? '—'}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{u.artifactCount}</td>
                  <td className="px-3 py-1.5 text-inkMuted">{u.lastLoginAt ? fmtDate(u.lastLoginAt) : '로그인 전'}</td>
                  <td className="px-3 py-1.5">
                    <Select value={u.role} disabled={self} className="h-7 w-auto text-xs" aria-label={`${u.name} 권한`}
                      onChange={(e) => update.mutate({ id: u.id, body: { role: e.target.value as AdminUser['role'] } })}>
                      <option value="user">사용자</option>
                      <option value="admin">관리자</option>
                    </Select>
                  </td>
                  <td className="px-3 py-1.5">
                    <button
                      disabled={self}
                      onClick={() => {
                        if (!u.isActive || confirm(`${u.name} 계정을 비활성화할까요? 로그인할 수 없게 되고, 등록한 산출물은 그대로 남습니다.`)) {
                          update.mutate({ id: u.id, body: { isActive: !u.isActive } })
                        }
                      }}
                      className="disabled:cursor-not-allowed"
                      title={self ? '자기 계정은 바꿀 수 없습니다' : '눌러서 전환'}
                    >
                      <Badge tone={u.isActive ? 'ok' : 'neutral'}>{u.isActive ? '활성' : '비활성'}</Badge>
                    </button>
                  </td>
                  {local && (
                    <td className="px-3 py-1.5">
                      {u.loginId && (
                        <Button variant="ghost" size="sm" disabled={reset.isPending}
                          onClick={() => confirm(`${u.name}의 비밀번호를 초기화할까요?`) && reset.mutate(u)}>
                          <KeyRound /> 초기화
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
