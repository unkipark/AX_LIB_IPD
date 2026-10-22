import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Library, LogIn, UserPlus } from 'lucide-react'
import { AccountFields, EMPTY_ACCOUNT, toSignupInput, type AccountDraft } from '@/components/AccountFields'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Field, Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import type { AuthConfig, User } from '@/types'

function safeNext(next: string | null) {
  return next && next.startsWith('/') && !next.startsWith('//') && next !== '/login' ? next : '/'
}

export function LoginPage({ config }: { config: AuthConfig }) {
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [account, setAccount] = useState<AccountDraft>(EMPTY_ACCOUNT)

  const done = (user: User) => {
    qc.setQueryData(['me'], user)
    navigate(next, { replace: true })
  }

  const run = async (fn: () => Promise<User>) => {
    setBusy(true)
    setError(null)
    try {
      done(await fn())
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <div className="flex w-full max-w-md flex-col gap-4">
        <div className="flex items-center justify-center gap-2">
          <Library className="size-5 text-accent" aria-hidden />
          <h1 className="text-lg font-semibold">AX 산출물 라이브러리</h1>
        </div>

        <Card>
          {config.mode === 'oidc' ? (
            <CardContent className="flex flex-col gap-3 py-6">
              <p className="text-center text-sm text-inkMuted">사내 SSO 계정으로 로그인합니다.</p>
              <Button asChild>
                <a href={`/api/auth/login?next=${encodeURIComponent(next)}`}>
                  <LogIn /> SSO 로그인
                </a>
              </Button>
            </CardContent>
          ) : (
            <Tabs defaultValue="login" onValueChange={() => setError(null)}>
              {config.signup && (
                <div className="border-b border-line px-3 py-2">
                  <TabsList>
                    <TabsTrigger value="login">로그인</TabsTrigger>
                    <TabsTrigger value="signup">가입</TabsTrigger>
                  </TabsList>
                </div>
              )}
              <TabsContent value="login">
                <form
                  className="flex flex-col gap-3 p-4"
                  onSubmit={(e) => {
                    e.preventDefault()
                    run(() => api.login(loginId, password))
                  }}
                >
                  <Field label="사번">
                    <Input value={loginId} onChange={(e) => setLoginId(e.target.value)} required autoFocus
                      autoComplete="username" />
                  </Field>
                  <Field label="비밀번호">
                    <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                      autoComplete="current-password" />
                  </Field>
                  {error && <p className="text-xs text-fail">{error}</p>}
                  <Button type="submit" disabled={busy}>
                    <LogIn /> 로그인
                  </Button>
                  <p className="text-center text-[11px] text-inkMuted">
                    비밀번호를 잊으셨다면 관리자에게 초기화를 요청하세요.
                    {!config.signup && ' 계정이 없으면 관리자에게 생성을 요청하세요.'}
                  </p>
                </form>
              </TabsContent>
              {config.signup && (
                <TabsContent value="signup">
                  <form
                    className="flex flex-col gap-3 p-4"
                    onSubmit={(e) => {
                      e.preventDefault()
                      const body = toSignupInput(account)
                      if (typeof body === 'string') return setError(body)
                      run(() => api.signup(body))
                    }}
                  >
                    <AccountFields value={account} onChange={setAccount} departments={config.departments} />
                    {error && <p className="text-xs text-fail">{error}</p>}
                    <Button type="submit" disabled={busy}>
                      <UserPlus /> 가입하고 시작하기
                    </Button>
                  </form>
                </TabsContent>
              )}
            </Tabs>
          )}
        </Card>
      </div>
    </div>
  )
}
