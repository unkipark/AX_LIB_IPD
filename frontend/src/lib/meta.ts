import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Meta } from '@/types'

const EMPTY: Meta = { types: [], statuses: [], tools: [] }

/** 분류 체계(유형·상태·AI 도구)와 key → 라벨 조회 함수. 원본은 backend/app/catalog.py 입니다. */
export function useMeta() {
  const { data = EMPTY } = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  const find = (list: Meta['types'], key: string) => list.find((o) => o.key === key)?.label ?? key
  return {
    meta: data,
    typeLabel: (k: string) => find(data.types, k),
    statusLabel: (k: string) => find(data.statuses, k),
    toolLabel: (k: string) => find(data.tools, k),
  }
}
