import { Field, Input } from '@/components/ui/input'
import type { SignupInput } from '@/types'

export type AccountDraft = SignupInput & { passwordConfirm: string }

export const EMPTY_ACCOUNT: AccountDraft = {
  loginId: '', password: '', passwordConfirm: '', name: '', department: '', email: '',
}

/** 가입 화면과 관리자 계정 생성에서 함께 씁니다. */
export function AccountFields({
  value,
  onChange,
  departments,
}: {
  value: AccountDraft
  onChange: (v: AccountDraft) => void
  departments: string[]
}) {
  const set = (k: keyof AccountDraft) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...value, [k]: e.target.value })
  return (
    <>
      <Field label="사번" required hint="로그인 ID 로 씁니다. 나중에 SSO 로 바뀌어도 사번으로 계정이 이어집니다.">
        <Input value={value.loginId} onChange={set('loginId')} required autoComplete="username"
          pattern="[A-Za-z0-9._\-]{2,50}" title="영문·숫자·. _ - 2~50자" />
      </Field>
      <Field label="이름" required>
        <Input value={value.name} onChange={set('name')} required maxLength={100} autoComplete="name" />
      </Field>
      <Field label="부서" hint="목록에 있으면 같은 표기를 골라주세요. 현황판 부서별 집계에 쓰입니다.">
        <Input value={value.department ?? ''} onChange={set('department')} list="department-options" maxLength={200} />
        <datalist id="department-options">
          {departments.map((d) => <option key={d} value={d} />)}
        </datalist>
      </Field>
      <Field label="이메일">
        <Input type="email" value={value.email ?? ''} onChange={set('email')} maxLength={200} autoComplete="email" />
      </Field>
      <Field label="비밀번호" required hint="8자 이상">
        <Input type="password" value={value.password} onChange={set('password')} required minLength={8}
          autoComplete="new-password" />
      </Field>
      <Field label="비밀번호 확인" required>
        <Input type="password" value={value.passwordConfirm} onChange={set('passwordConfirm')} required minLength={8}
          autoComplete="new-password" />
      </Field>
    </>
  )
}

/** 화면 검증 후 API 로 보낼 값. 비밀번호 확인이 다르면 오류 메시지를 돌려줍니다. */
export function toSignupInput(v: AccountDraft): SignupInput | string {
  if (v.password !== v.passwordConfirm) return '비밀번호 확인이 일치하지 않습니다'
  const { passwordConfirm: _, ...rest } = v
  return { ...rest, department: v.department || null, email: v.email || null }
}
