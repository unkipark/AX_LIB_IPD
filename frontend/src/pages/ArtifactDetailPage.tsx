import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, ExternalLink, Pencil, ThumbsUp, Trash2 } from 'lucide-react'
import { Markdown } from '@/components/Markdown'
import { StatusBadge } from '@/components/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import { useMeta } from '@/lib/meta'
import { fmtBytes, fmtDate } from '@/lib/utils'

export function ArtifactDetailPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { typeLabel, toolLabel } = useMeta()
  const { data: a, error } = useQuery({ queryKey: ['artifact', id], queryFn: () => api.get(id) })

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['artifact', id] })
    qc.invalidateQueries({ queryKey: ['artifacts'] })
    qc.invalidateQueries({ queryKey: ['dashboard'] })
  }
  const used = useMutation({ mutationFn: () => api.markUsed(id), onSuccess: refresh })
  const remove = useMutation({
    mutationFn: () => api.remove(id),
    onSuccess: () => {
      refresh()
      navigate('/artifacts')
    },
  })

  if (error) return <p className="text-sm text-fail">{(error as Error).message}</p>
  if (!a) return <p className="text-sm text-inkMuted">불러오는 중…</p>

  const meta: [string, React.ReactNode][] = [
    ['유형', typeLabel(a.type)],
    ['상태', <StatusBadge key="s" status={a.status} />],
    ['개선 대상 업무', a.process || '—'],
    ['버전', a.version || '—'],
    ['1회 절감 시간', a.timeSavedMin != null ? `${a.timeSavedMin}분` : '—'],
    ['등록자', `${a.owner.name}${a.department ? ` · ${a.department}` : ''}`],
    ['등록일', fmtDate(a.createdAt)],
    ['수정일', fmtDate(a.updatedAt)],
    ['다운로드', `${a.downloadCount}회`],
  ]

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Link to="/artifacts" className="text-xs text-inkMuted hover:text-ink">← 산출물 목록</Link>
          <h2 className="text-xl font-semibold">{a.title}</h2>
          <p className="text-sm text-inkMuted">{a.summary}</p>
          <div className="flex flex-wrap gap-1">
            {a.tools.map((t) => <Badge key={t} tone="info">{toolLabel(t)}</Badge>)}
            {a.tags.map((t) => (
              <Link key={t} to={`/artifacts?q=${encodeURIComponent(t)}`}>
                <Badge>#{t}</Badge>
              </Link>
            ))}
          </div>
        </div>

        <Card>
          <Tabs defaultValue="description">
            <CardHeader>
              <TabsList>
                <TabsTrigger value="description">설명</TabsTrigger>
                <TabsTrigger value="install">설치 · 사용법</TabsTrigger>
              </TabsList>
            </CardHeader>
            <TabsContent value="description" className="p-4">
              <Markdown>{a.description}</Markdown>
            </TabsContent>
            <TabsContent value="install" className="p-4">
              <Markdown>{a.installGuide}</Markdown>
            </TabsContent>
          </Tabs>
        </Card>
      </div>

      <aside className="flex flex-col gap-4">
        <Card>
          <CardContent className="flex flex-col gap-2">
            <Button onClick={() => used.mutate()} disabled={a.usedByMeToday || used.isPending}>
              <ThumbsUp /> {a.usedByMeToday ? '오늘 사용 기록됨' : '써봤어요'}
              <span className="font-mono">{a.useCount}</span>
            </Button>
            <p className="text-[11px] text-inkMuted">
              업무에 실제로 사용했다면 눌러주세요. 현황판의 사용 횟수와 절감 시간에 반영됩니다(하루 1회).
            </p>
            {a.repoUrl && (
              <Button asChild variant="outline">
                <a href={a.repoUrl} target="_blank" rel="noreferrer">
                  <ExternalLink /> 저장소 열기
                </a>
              </Button>
            )}
            {a.canEdit && (
              <div className="flex gap-2">
                <Button asChild variant="outline" className="flex-1">
                  <Link to={`/artifacts/${a.id}/edit`}>
                    <Pencil /> 수정
                  </Link>
                </Button>
                <Button
                  variant="outline"
                  className="text-fail"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (confirm(`'${a.title}' 을(를) 삭제할까요? 첨부파일과 사용 기록도 함께 삭제됩니다.`)) remove.mutate()
                  }}
                >
                  <Trash2 /> 삭제
                </Button>
              </div>
            )}
            {(used.error || remove.error) && (
              <p className="text-xs text-fail">{((used.error || remove.error) as Error).message}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>정보</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-xs">
              {meta.map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-inkMuted">{k}</dt>
                  <dd className="text-right text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>첨부파일</CardTitle>
            <span className="font-mono text-xs text-inkMuted">{a.files.length}</span>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {a.files.length === 0 && <p className="text-xs text-inkMuted">첨부파일이 없습니다.</p>}
            {a.files.map((f) => (
              <a
                key={f.id}
                href={api.fileUrl(f.id)}
                onClick={() => setTimeout(refresh, 500)}
                className="flex items-center gap-2 rounded-panel px-1.5 py-1 text-xs hover:bg-panelRaised"
              >
                <Download className="size-3.5 shrink-0 text-inkMuted" aria-hidden />
                <span className="truncate text-ink">{f.name}</span>
                <span className="ml-auto shrink-0 font-mono text-inkMuted">{fmtBytes(f.size)}</span>
              </a>
            ))}
          </CardContent>
        </Card>
      </aside>
    </div>
  )
}
