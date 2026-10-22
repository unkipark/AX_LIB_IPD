import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { KeyRound, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import type { AuthConfig, User } from '@/types'

type Msg = { ok: boolean; text: string } | null

function Message({ msg }: { msg: Msg }) {
  if (!msg) return null
  return <p className={msg.ok ? 'text-xs text-ok' : 'text-xs text-fail'}>{msg.text}</p>
}

export function ProfilePage({ user, config }: { user: User; config: AuthConfig }) {
  const qc = useQueryClient()
  const local = config.mode === 'local'
  const [profile, setProfile] = useState({ name: user.name, department: user.department ?? '', email: user.email ?? '' })
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [profileMsg, setProfileMsg] = useState<Msg>(null)
  const [pwMsg, setPwMsg] = useState<Msg>(null)

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const updated = await api.updateMe({
        name: profile.name, department: profile.department || null, email: profile.email || null,
      })
      qc.setQueryData(['me'], updated)
      qc.invalidateQueries({ queryKey: ['authConfig'] })
      setProfileMsg({ ok: true, text: '저장했습니다. 이미 등록한 산출물의 부서는 등록 당시 값으로 남습니다.' })
    } catch (err) {
      setProfileMsg({ ok: false, text: (err as Error).message })
    }
  }

  const savePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (pw.next !== pw.confirm) return setPwMsg({ ok: false, text: '새 비밀번호 확인이 일치하지 않습니다' })
    try {
      await api.changePassword(pw.current, pw.next)
      setPw({ current: '', next: '', confirm: '' })
      setPwMsg({ ok: true, text: '비밀번호를 바꿨습니다.' })
    } catch (err) {
      setPwMsg({ ok: false, text: (err as Error).message })
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <h2 className="text-lg font-semibold">내 정보</h2>

      <Card>
        <CardHeader><CardTitle>프로필</CardTitle></CardHeader>
        <CardContent>
          {local ? (
            <form onSubmit={saveProfile} className="flex flex-col gap-3">
              <Field label="사번">
                <Input value={user.loginId ?? ''} disabled />
              </Field>
              <Field label="이름" required>
                <Input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} required />
              </Field>
              <Field label="부서">
                <Input value={profile.department} list="profile-departments"
                  onChange={(e) => setProfile({ ...profile, department: e.target.value })} />
                <datalist id="profile-departments">
                  {config.departments.map((d) => <option key={d} value={d} />)}
                </datalist>
              </Field>
              <Field label="이메일">
                <Input type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} />
              </Field>
              <Message msg={profileMsg} />
              <Button type="submit" className="self-end"><Save /> 저장</Button>
            </form>
          ) : (
            <dl className="grid grid-cols-[6rem_1fr] gap-y-1.5 text-sm">
              <dt className="text-inkMuted">이름</dt><dd>{user.name}</dd>
              <dt className="text-inkMuted">부서</dt><dd>{user.department ?? '—'}</dd>
              <dt className="text-inkMuted">이메일</dt><dd>{user.email ?? '—'}</dd>
              <dd className="col-span-2 pt-2 text-xs text-inkMuted">SSO 정보로 로그인할 때마다 자동 갱신됩니다.</dd>
            </dl>
          )}
        </CardContent>
      </Card>

      {local && (
        <Card>
          <CardHeader><CardTitle>비밀번호 변경</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={savePassword} className="flex flex-col gap-3">
              <Field label="현재 비밀번호" required>
                <Input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })}
                  required autoComplete="current-password" />
              </Field>
              <Field label="새 비밀번호" required hint="8자 이상">
                <Input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })}
                  required minLength={8} autoComplete="new-password" />
              </Field>
              <Field label="새 비밀번호 확인" required>
                <Input type="password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
                  required minLength={8} autoComplete="new-password" />
              </Field>
              <Message msg={pwMsg} />
              <Button type="submit" className="self-end"><KeyRound /> 비밀번호 변경</Button>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
