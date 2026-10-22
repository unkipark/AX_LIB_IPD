import type { ArtifactDetail, ArtifactInput, ArtifactPage, Dashboard, FileInfo, Meta, User } from '@/types'

/** 배포 시 FastAPI 가 같은 오리진에서 정적 파일을 서빙하므로 상대경로면 충분합니다. */
const BASE = '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

/** 세션이 없으면 SSO 로그인으로 보내고, 로그인 후 지금 보던 화면으로 돌아옵니다. */
export function goLogin() {
  const next = window.location.pathname + window.location.search
  window.location.href = `${BASE}/auth/login?next=${encodeURIComponent(next)}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (res.status === 401) {
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
  me: () => request<User>('/me'),
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
