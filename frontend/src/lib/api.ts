import type {
  AdminUser,
  ArtifactDetail,
  ArtifactInput,
  ArtifactPage,
  AuthConfig,
  Dashboard,
  FileInfo,
  Meta,
  SignupInput,
  User,
} from '@/types'

/** 배포 시 FastAPI 가 같은 오리진에서 정적 파일을 서빙하므로 상대경로면 충분합니다. */
const BASE = '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

let authMode: AuthConfig['mode'] = 'local'

/** App 이 /api/auth/config 를 읽은 뒤 호출합니다. 401 때 어느 로그인으로 보낼지 정합니다. */
export function setAuthMode(mode: AuthConfig['mode']) {
  authMode = mode
}

/** 세션이 없으면 로그인 화면(local) 또는 SSO(oidc)로 보내고, 로그인 후 지금 보던 화면으로 돌아옵니다. */
export function goLogin() {
  if (window.location.pathname === '/login') return
  const next = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = authMode === 'oidc' ? `${BASE}/auth/login?next=${next}` : `/login?next=${next}`
}

async function request<T>(path: string, init?: RequestInit, redirectOn401 = true): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (res.status === 401 && redirectOn401) {
    goLogin()
    throw new ApiError(401, '로그인이 필요합니다')
  }
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(', ')
    } catch {
      // 본문이 JSON 이 아니면 상태줄만 보여줍니다.
    }
    throw new ApiError(res.status, message)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

const jsonBody = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export interface ListParams {
  q?: string
  type?: string
  status?: string
  tool?: string
  department?: string
  mine?: boolean
  sort?: 'recent' | 'popular' | 'title'
  page?: number
}

export const api = {
  authConfig: () => request<AuthConfig>('/auth/config'),
  // 로그인 실패(401)는 화면에 메시지로 보여야 하므로 로그인 화면으로 다시 보내지 않습니다.
  login: (loginId: string, password: string) =>
    request<User>('/auth/local/login', jsonBody('POST', { loginId, password }), false),
  signup: (body: SignupInput) => request<User>('/auth/local/signup', jsonBody('POST', body), false),
  me: () => request<User>('/me'),
  updateMe: (body: Pick<User, 'name' | 'department' | 'email'>) => request<User>('/me', jsonBody('PUT', body)),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>('/me/password', jsonBody('PUT', { currentPassword, newPassword })),

  adminUsers: () => request<AdminUser[]>('/admin/users'),
  adminCreateUser: (body: SignupInput) => request<AdminUser>('/admin/users', jsonBody('POST', body)),
  adminUpdateUser: (id: number, body: Partial<Pick<AdminUser, 'role' | 'isActive'>>) =>
    request<AdminUser>(`/admin/users/${id}`, jsonBody('PUT', body)),
  adminResetPassword: (id: number) =>
    request<{ tempPassword: string }>(`/admin/users/${id}/reset-password`, { method: 'POST' }),

  meta: () => request<Meta>('/meta'),
  dashboard: () => request<Dashboard>('/dashboard'),

  list(params: ListParams) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '' && v !== false) qs.set(k, String(v))
    }
    return request<ArtifactPage>(`/artifacts?${qs}`)
  },
  get: (id: number) => request<ArtifactDetail>(`/artifacts/${id}`),
  create: (body: ArtifactInput) => request<ArtifactDetail>('/artifacts', jsonBody('POST', body)),
  update: (id: number, body: ArtifactInput) => request<ArtifactDetail>(`/artifacts/${id}`, jsonBody('PUT', body)),
  remove: (id: number) => request<void>(`/artifacts/${id}`, { method: 'DELETE' }),
  markUsed: (id: number) => request<{ useCount: number }>(`/artifacts/${id}/used`, { method: 'POST' }),

  upload(artifactId: number, file: File) {
    const form = new FormData()
    form.append('file', file)
    return request<FileInfo>(`/artifacts/${artifactId}/files`, { method: 'POST', body: form })
  },
  removeFile: (fileId: number) => request<void>(`/files/${fileId}`, { method: 'DELETE' }),
  fileUrl: (fileId: number) => `${BASE}/files/${fileId}`,
}
