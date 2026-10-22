export interface Option {
  key: string
  label: string
}

export interface Meta {
  types: Option[]
  statuses: Option[]
  tools: Option[]
}

export interface AuthConfig {
  mode: 'local' | 'oidc'
  signup: boolean
  departments: string[]
}

export interface User {
  id: number
  loginId: string | null
  name: string
  email: string | null
  department: string | null
  empNo: string | null
  role: 'user' | 'admin'
}

export interface Owner {
  id: number
  name: string
  department: string | null
}

export interface ArtifactInput {
  title: string
  summary: string
  description: string
  installGuide: string
  type: string
  status: string
  process: string
  version: string
  repoUrl: string
  timeSavedMin: number | null
  tools: string[]
  tags: string[]
}

export interface ArtifactSummary {
  id: number
  title: string
  summary: string
  type: string
  status: string
  tools: string[]
  tags: string[]
  owner: Owner
  department: string | null
  timeSavedMin: number | null
  useCount: number
  fileCount: number
  createdAt: string
  updatedAt: string
}

export interface FileInfo {
  id: number
  name: string
  size: number
  contentType: string
  createdAt: string
}

export interface ArtifactDetail extends ArtifactSummary {
  description: string
  installGuide: string
  process: string
  version: string
  repoUrl: string
  files: FileInfo[]
  downloadCount: number
  usedByMeToday: boolean
  canEdit: boolean
}

export interface ArtifactPage {
  items: ArtifactSummary[]
  total: number
}

export interface CountRow {
  key: string
  label: string
  count: number
}

export interface ArtifactRef {
  id: number
  title: string
  type: string
  status: string
}

export interface Dashboard {
  kpi: {
    artifacts: number
    deployed: number
    contributors: number
    uses: number
    users: number
    downloads: number
    savedHours: number
  }
  byStatus: CountRow[]
  byType: CountRow[]
  byTool: CountRow[]
  byDepartment: CountRow[]
  monthly: { month: string; created: number; used: number }[]
  topUsed: (ArtifactRef & { uses: number; savedHours: number })[]
  topContributors: { id: number; name: string; department: string | null; count: number }[]
  recent: (ArtifactRef & { createdAt: string })[]
}

export interface SignupInput {
  loginId: string
  password: string
  name: string
  department: string | null
  email: string | null
}

export interface AdminUser {
  id: number
  loginId: string | null
  empNo: string | null
  name: string
  email: string | null
  department: string | null
  role: 'user' | 'admin'
  isActive: boolean
  lastLoginAt: string | null
  artifactCount: number
}
