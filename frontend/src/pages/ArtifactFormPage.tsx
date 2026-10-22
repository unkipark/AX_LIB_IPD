import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Paperclip, Save, X } from 'lucide-react'
import { Markdown } from '@/components/Markdown'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, Input, Select, Textarea } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import { useMeta } from '@/lib/meta'
import { cn, fmtBytes } from '@/lib/utils'
import type { ArtifactInput, FileInfo } from '@/types'

/** 새 산출물의 설명 기본값. 현황판에 필요한 Before/After 를 자연스럽게 적도록 유도합니다. */
const DESCRIPTION_TEMPLATE = `## 배경 (Before)
- 어떤 업무를, 얼마나 자주, 얼마나 걸려서 하고 있었나요?

## 개선 내용 (After)
- AI 도구를 어떻게 활용했나요?

## 효과
- 1회 기준 절감 시간, 품질 변화 등

## 제약 · 주의사항
-
`

const EMPTY: ArtifactInput = {
  title: '',
  summary: '',
  description: DESCRIPTION_TEMPLATE,
  installGuide: '',
  type: 'skill',
  status: 'developing',
  process: '',
  version: '',
  repoUrl: '',
  timeSavedMin: null,
  tools: [],
  tags: [],
}

export function ArtifactFormPage() {
  const params = useParams()
  const editId = params.id ? Number(params.id) : null
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { meta } = useMeta()

  const existing = useQuery({
    queryKey: ['artifact', editId],
    queryFn: () => api.get(editId!),
    enabled: editId !== null,
  })

  const [form, setForm] = useState<ArtifactInput>(EMPTY)
  const [tagText, setTagText] = useState('')
  const [files, setFiles] = useState<FileInfo[]>([])
  const [pending, setPending] = useState<File[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const a = existing.data
    if (!a) return
    setForm({
      title: a.title, summary: a.summary, description: a.description, installGuide: a.installGuide,
      type: a.type, status: a.status, process: a.process, version: a.version, repoUrl: a.repoUrl,
      timeSavedMin: a.timeSavedMin, tools: a.tools, tags: a.tags,
    })
    setTagText(a.tags.join(', '))
    setFiles(a.files)
  }, [existing.data])

  if (existing.data && !existing.data.canEdit) {
    return <p className="text-sm text-fail">등록자 또는 관리자만 수정할 수 있습니다.</p>
  }

  const set = <K extends keyof ArtifactInput>(key: K, value: ArtifactInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  const toggleTool = (key: string) =>
    set('tools', form.tools.includes(key) ? form.tools.filter((t) => t !== key) : [...form.tools, key])

  const removeExistingFile = async (f: FileInfo) => {
    if (!confirm(`'${f.name}' 을(를) 삭제할까요?`)) return
    try {
      await api.removeFile(f.id)
      setFiles((fs) => fs.filter((x) => x.id !== f.id))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    const body = { ...form, tags: tagText.split(',').map((t) => t.trim()).filter(Boolean) }
    try {
      const saved = editId ? await api.update(editId, body) : await api.create(body)
      // 본문 저장이 끝난 뒤 첨부파일을 하나씩 올립니다. 실패한 파일은 수정 화면에서 다시 올리면 됩니다.
      for (const file of pending) await api.upload(saved.id, file)
      qc.invalidateQueries({ queryKey: ['artifacts'] })
      qc.invalidateQueries({ queryKey: ['artifact', saved.id] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      navigate(`/artifacts/${saved.id}`)
    } catch (err) {
      setError((err as Error).message)
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto flex max-w-4xl flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{editId ? '산출물 수정' : '산출물 등록'}</h2>
        <p className="text-xs text-inkMuted">등록자·부서는 계정 정보로 자동 입력됩니다.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>기본 정보</CardTitle></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <Field label="제목" required className="sm:col-span-2">
            <Input value={form.title} onChange={(e) => set('title', e.target.value)} maxLength={200} required
              placeholder="예) PR 리뷰 초안 자동 생성 skill" />
          </Field>
          <Field label="한 줄 요약" required className="sm:col-span-2">
            <Input value={form.summary} onChange={(e) => set('summary', e.target.value)} maxLength={500} required
              placeholder="무엇을 해주는지 한 문장으로" />
          </Field>
          <Field label="유형" required>
            <Select value={form.type} onChange={(e) => set('type', e.target.value)}>
              {meta.types.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
            </Select>
          </Field>
          <Field label="상태" required>
            <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
              {meta.statuses.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
            </Select>
          </Field>
          <div className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-xs font-medium text-inkMuted">사용한 AI 도구</span>
            <div className="flex flex-wrap gap-1.5">
              {meta.tools.map((o) => {
                const on = form.tools.includes(o.key)
                return (
                  <button
                    key={o.key}
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggleTool(o.key)}
                    className={cn(
                      'rounded-panel border px-2.5 py-1 text-xs transition-colors',
                      on ? 'border-accent bg-accent/15 text-ink' : 'border-line text-inkMuted hover:text-ink'
                    )}
                  >
                    {o.label}
                  </button>
                )
              })}
            </div>
          </div>
          <Field label="개선 대상 업무 프로세스">
            <Input value={form.process} onChange={(e) => set('process', e.target.value)} maxLength={200}
              placeholder="예) 코드 리뷰, 주간 보고서 작성" />
          </Field>
          <Field label="1회 사용 시 절감 시간 (분)" hint="현황판의 누적 절감 시간 = 이 값 × 사용 기록 수">
            <Input type="number" min={0} value={form.timeSavedMin ?? ''}
              onChange={(e) => set('timeSavedMin', e.target.value === '' ? null : Number(e.target.value))} />
          </Field>
          <Field label="버전">
            <Input value={form.version} onChange={(e) => set('version', e.target.value)} maxLength={50} placeholder="예) v1.0" />
          </Field>
          <Field label="저장소 URL">
            <Input value={form.repoUrl} onChange={(e) => set('repoUrl', e.target.value)} maxLength={500}
              placeholder="http://..." />
          </Field>
          <Field label="태그" hint="쉼표로 구분, 최대 10개" className="sm:col-span-2">
            <Input value={tagText} onChange={(e) => setTagText(e.target.value)} placeholder="리뷰, 자동화, 보고서" />
          </Field>
        </CardContent>
      </Card>

      <MarkdownField label="설명" value={form.description} onChange={(v) => set('description', v)} rows={14} />
      <MarkdownField
        label="설치 · 사용법"
        value={form.installGuide}
        onChange={(v) => set('installGuide', v)}
        rows={8}
        placeholder={'예)\n```bash\ncp -r review-skill ~/.claude/skills/\n```\nClaude Code 에서 /review 실행'}
      />

      <Card>
        <CardHeader><CardTitle>첨부파일</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2">
          {files.map((f) => (
            <div key={f.id} className="flex items-center gap-2 text-xs">
              <Paperclip className="size-3.5 text-inkMuted" aria-hidden />
              <span className="truncate">{f.name}</span>
              <span className="font-mono text-inkMuted">{fmtBytes(f.size)}</span>
              <Button type="button" variant="ghost" size="sm" className="ml-auto" onClick={() => removeExistingFile(f)}>
                <X /> 삭제
              </Button>
            </div>
          ))}
          {pending.map((f, i) => (
            <div key={`${f.name}-${i}`} className="flex items-center gap-2 text-xs">
              <Paperclip className="size-3.5 text-accent" aria-hidden />
              <span className="truncate">{f.name}</span>
              <span className="font-mono text-inkMuted">{fmtBytes(f.size)} · 저장 시 업로드</span>
              <Button type="button" variant="ghost" size="sm" className="ml-auto"
                onClick={() => setPending((p) => p.filter((_, j) => j !== i))}>
                <X /> 취소
              </Button>
            </div>
          ))}
          <input
            type="file"
            multiple
            onChange={(e) => {
              // 아래에서 input 을 비우므로 FileList 를 먼저 복사해 둡니다.
              const picked = Array.from(e.target.files ?? [])
              setPending((p) => [...p, ...picked])
              e.target.value = ''
            }}
            className="text-xs text-inkMuted file:mr-2 file:rounded-panel file:border file:border-line file:bg-panelRaised file:px-2 file:py-1 file:text-xs file:text-ink"
          />
          <p className="text-[11px] text-inkMuted">skill 폴더·스크립트는 zip 으로 묶어 올리세요.</p>
        </CardContent>
      </Card>

      {error && <p className="rounded-panel border border-fail/40 bg-fail/10 px-3 py-2 text-xs text-fail">{error}</p>}

      <div className="flex justify-end gap-2">
        <Button asChild variant="outline">
          <Link to={editId ? `/artifacts/${editId}` : '/artifacts'}>취소</Link>
        </Button>
        <Button type="submit" disabled={saving}>
          <Save /> {saving ? '저장 중…' : '저장'}
        </Button>
      </div>
    </form>
  )
}

function MarkdownField({
  label,
  value,
  onChange,
  rows,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  rows: number
  placeholder?: string
}) {
  return (
    <Card>
      <Tabs defaultValue="write">
        <CardHeader>
          <CardTitle>{label} <span className="font-normal text-inkMuted">(Markdown)</span></CardTitle>
          <TabsList>
            <TabsTrigger value="write">작성</TabsTrigger>
            <TabsTrigger value="preview">미리보기</TabsTrigger>
          </TabsList>
        </CardHeader>
        <TabsContent value="write" className="p-3">
          <Textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows} placeholder={placeholder} />
        </TabsContent>
        <TabsContent value="preview" className="p-4">
          <Markdown>{value}</Markdown>
        </TabsContent>
      </Tabs>
    </Card>
  )
}
