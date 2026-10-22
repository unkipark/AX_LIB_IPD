import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { ArtifactCard } from '@/components/ArtifactCard'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/input'
import { api, type ListParams } from '@/lib/api'
import { useMeta } from '@/lib/meta'

const PAGE_SIZE = 24

/** 필터는 모두 URL 쿼리에 둡니다. 링크로 공유하거나 뒤로 가기를 해도 상태가 유지됩니다. */
export function CatalogPage() {
  const { meta } = useMeta()
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')

  const filters: ListParams = {
    q: params.get('q') ?? '',
    type: params.get('type') ?? '',
    status: params.get('status') ?? '',
    tool: params.get('tool') ?? '',
    department: params.get('department') ?? '',
    mine: params.get('mine') === 'true',
    sort: (params.get('sort') as ListParams['sort']) ?? 'recent',
    page: Number(params.get('page') ?? 1),
  }

  const { data, isLoading } = useQuery({
    queryKey: ['artifacts', filters],
    queryFn: () => api.list(filters),
    placeholderData: (prev) => prev,
  })

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== 'page') next.delete('page')
    setParams(next)
  }

  // 입력이 멈추고 0.3초 뒤에 검색합니다.
  useEffect(() => {
    const id = setTimeout(() => {
      if (q !== (params.get('q') ?? '')) set('q', q)
    }, 300)
    return () => clearTimeout(id)
  }, [q])

  const total = data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-2 top-2 size-4 text-inkMuted" aria-hidden />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="제목·요약·업무·태그 검색"
            className="pl-8"
            aria-label="검색"
          />
        </div>
        <Select value={filters.type} onChange={(e) => set('type', e.target.value)} className="w-auto" aria-label="유형">
          <option value="">전체 유형</option>
          {meta.types.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        </Select>
        <Select value={filters.status} onChange={(e) => set('status', e.target.value)} className="w-auto" aria-label="상태">
          <option value="">전체 상태</option>
          {meta.statuses.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        </Select>
        <Select value={filters.tool} onChange={(e) => set('tool', e.target.value)} className="w-auto" aria-label="AI 도구">
          <option value="">전체 AI 도구</option>
          {meta.tools.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
        </Select>
        <label className="flex items-center gap-1.5 text-xs text-inkMuted">
          <input
            type="checkbox"
            checked={filters.mine}
            onChange={(e) => set('mine', e.target.checked ? 'true' : '')}
            className="accent-[rgb(var(--c-accent))]"
          />
          내 산출물만
        </label>
        <Select
          value={filters.sort}
          onChange={(e) => set('sort', e.target.value === 'recent' ? '' : e.target.value)}
          className="ml-auto w-auto"
          aria-label="정렬"
        >
          <option value="recent">최근 수정순</option>
          <option value="popular">많이 쓰인 순</option>
          <option value="title">제목순</option>
        </Select>
      </div>

      {filters.department && (
        <p className="text-xs text-inkMuted">
          부서: <span className="text-ink">{filters.department}</span>{' '}
          <button className="underline" onClick={() => set('department', '')}>해제</button>
        </p>
      )}

      <p className="text-xs text-inkMuted">총 {total.toLocaleString()}건</p>

      {isLoading ? (
        <p className="py-12 text-center text-sm text-inkMuted">불러오는 중…</p>
      ) : total === 0 ? (
        <p className="py-12 text-center text-sm text-inkMuted">조건에 맞는 산출물이 없습니다.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data?.items.map((a) => <ArtifactCard key={a.id} a={a} />)}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2 text-xs text-inkMuted">
          <Button variant="outline" size="sm" disabled={filters.page! <= 1} onClick={() => set('page', String(filters.page! - 1))}>
            <ChevronLeft /> 이전
          </Button>
          <span className="font-mono">{filters.page} / {pages}</span>
          <Button variant="outline" size="sm" disabled={filters.page! >= pages} onClick={() => set('page', String(filters.page! + 1))}>
            다음 <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}
