import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Bot, Check, Loader2, MessageSquarePlus, Search, SendHorizontal, Square, Trash2 } from 'lucide-react'
import { Markdown } from '@/components/Markdown'
import { Button } from '@/components/ui/button'
import { api, streamAgentMessage } from '@/lib/api'
import { cn, fmtDate } from '@/lib/utils'
import type { AgentMessage, AgentToolCall } from '@/types'

const STARTERS = [
  '주간보고 작성 시간을 줄일 수 있는 산출물 있어?',
  '코드 리뷰에 쓸 만한 Claude Code skill 추천해줘',
  '요즘 많이 쓰이는 산출물 알려줘',
  '회의록 정리를 자동화할 방법이 있을까?',
]

function toolLabel(t: AgentToolCall) {
  if (t.name === 'search_artifacts') return `검색: "${String(t.input.query ?? '').slice(0, 40)}"`
  if (t.name === 'get_artifact') return `상세 확인 #${String(t.input.artifact_id ?? '')}`
  if (t.name === 'get_overview') return '전체 현황 확인'
  return t.name
}

function ToolChip({ t, running }: { t: AgentToolCall; running: boolean }) {
  const done = t.isError !== undefined
  return (
    <span className="inline-flex items-center gap-1 rounded-panel border border-line bg-panelRaised px-1.5 py-0.5 text-[11px] text-inkMuted">
      {t.name === 'search_artifacts' ? <Search className="size-3" aria-hidden /> : null}
      {toolLabel(t)}
      {!done && running && <Loader2 className="size-3 animate-spin" aria-label="진행 중" />}
      {done && !t.isError && <Check className="size-3 text-ok" aria-label="완료" />}
      {t.isError && <AlertTriangle className="size-3 text-fail" aria-label="실패" />}
    </span>
  )
}

function Bubble({ m }: { m: AgentMessage }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-panel bg-accent/15 px-3 py-2 text-sm text-ink">{m.content}</div>
      </div>
    )
  }
  return (
    <div className="flex gap-2">
      <Bot className="mt-1 size-4 shrink-0 text-accent" aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        {m.tools.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {m.tools.map((t, i) => <ToolChip key={i} t={t} running={!!m.pending} />)}
          </div>
        )}
        {m.content ? (
          <Markdown>{m.content}</Markdown>
        ) : m.pending ? (
          <p className="flex items-center gap-1.5 text-xs text-inkMuted"><Loader2 className="size-3 animate-spin" /> 생각하는 중…</p>
        ) : null}
        {m.error && (
          <p className="flex items-start gap-1.5 rounded-panel border border-fail/40 bg-fail/10 px-2 py-1 text-xs text-fail">
            <AlertTriangle className="mt-0.5 size-3 shrink-0" /> {m.error}
          </p>
        )}
      </div>
    </div>
  )
}

export function AgentPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const status = useQuery({ queryKey: ['agentStatus'], queryFn: api.agentStatus })
  const list = useQuery({ queryKey: ['agentConversations'], queryFn: api.agentConversations })
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  // 첫 질문으로 대화를 만들면 URL 이 바뀌는데, 그때 진행 중인 답변을 서버 기록으로 덮어쓰지 않게 합니다.
  const skipLoadRef = useRef<string | null>(null)

  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      return
    }
    if (skipLoadRef.current === conversationId) {
      skipLoadRef.current = null // 한 번만 건너뜁니다. 다른 대화에 갔다 오면 다시 읽어야 합니다.
      return
    }
    // 다른 화면에 다녀오거나 새로고침했는데 답변이 아직 생성 중이면, 끝날 때까지 2초마다 다시 읽습니다.
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const load = () =>
      api.agentGet(conversationId)
        .then((c) => {
          if (!alive) return
          setMessages(c.running
            ? [...c.messages, { id: 'running', role: 'assistant', content: '', tools: [], error: null, pending: true }]
            : c.messages)
          setBusy(c.running)
          if (c.running) timer = setTimeout(load, 2000)
        })
        .catch((e: Error) => alive && setNotice(e.message))
    load()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [conversationId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  // 화면을 떠나면 응답 스트림 읽기만 멈춥니다. 서버의 답변 생성은 계속되어 기록에 남습니다.
  useEffect(() => () => abortRef.current?.abort(), [])

  const stop = () => {
    if (conversationId) api.agentCancel(conversationId).catch(() => undefined)
    abortRef.current?.abort()
  }

  const patchLast = (fn: (m: AgentMessage) => AgentMessage) =>
    setMessages((ms) => [...ms.slice(0, -1), fn(ms[ms.length - 1])])

  const send = async (text: string) => {
    const content = text.trim()
    if (!content || busy) return
    setBusy(true)
    setNotice(null)
    setInput('')
    let id = conversationId
    try {
      if (!id) {
        id = (await api.agentCreate()).id
        skipLoadRef.current = id
        navigate(`/agent/${id}`, { replace: true })
      }
      setMessages((ms) => [
        ...ms,
        { id: `u${Date.now()}`, role: 'user', content, tools: [], error: null },
        { id: `a${Date.now()}`, role: 'assistant', content: '', tools: [], error: null, pending: true },
      ])
      const abort = new AbortController()
      abortRef.current = abort
      await streamAgentMessage(id, content, (e) => {
        if (e.type === 'text') patchLast((m) => ({ ...m, content: m.content + e.delta }))
        else if (e.type === 'tool') patchLast((m) => ({ ...m, tools: [...m.tools, { name: e.name, input: e.input }] }))
        else if (e.type === 'tool_done')
          patchLast((m) => {
            const i = m.tools.findIndex((t) => t.name === e.name && t.isError === undefined)
            return i < 0 ? m : { ...m, tools: m.tools.map((t, j) => (j === i ? { ...t, isError: e.isError } : t)) }
          })
        else if (e.type === 'status') setNotice(e.text)
        else if (e.type === 'error') patchLast((m) => ({ ...m, error: e.message }))
        if (e.type !== 'status') setNotice(null)
      }, abort.signal)
    } catch (e) {
      const aborted = (e as Error).name === 'AbortError'
      setMessages((ms) => {
        const last = ms[ms.length - 1]
        if (last?.role === 'assistant' && last.pending) {
          return [...ms.slice(0, -1), { ...last, error: aborted ? '중단했습니다.' : (e as Error).message }]
        }
        return ms
      })
      if (!aborted && !conversationId && !id) setNotice((e as Error).message)
    } finally {
      setMessages((ms) => ms.map((m) => (m.pending ? { ...m, pending: false } : m)))
      setBusy(false)
      abortRef.current = null
      qc.invalidateQueries({ queryKey: ['agentConversations'] })
    }
  }

  const remove = async (id: string) => {
    if (!confirm('이 대화를 삭제할까요?')) return
    await api.agentDelete(id)
    qc.invalidateQueries({ queryKey: ['agentConversations'] })
    if (id === conversationId) navigate('/agent')
  }

  if (status.data && !status.data.enabled) {
    return (
      <p className="text-sm text-inkMuted">
        AI 도우미가 꺼져 있습니다. 관리자에게 문의하세요. <span className="font-mono text-xs">({status.data.reason})</span>
      </p>
    )
  }

  return (
    <div className="grid h-[calc(100vh-7rem)] min-h-[480px] gap-3 md:grid-cols-[220px_1fr]">
      <aside className="hidden min-h-0 flex-col gap-2 md:flex">
        <Button variant="outline" onClick={() => navigate('/agent')} disabled={busy}>
          <MessageSquarePlus /> 새 대화
        </Button>
        <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto" aria-label="대화 목록">
          {(list.data ?? []).map((c) => (
            <div key={c.id} className={cn('group flex items-center rounded-panel', c.id === conversationId && 'bg-panelRaised')}>
              <Link to={`/agent/${c.id}`} className="min-w-0 flex-1 px-2 py-1.5 text-xs">
                <span className="block truncate text-ink">{c.title}</span>
                <span className="text-[11px] text-inkMuted">{fmtDate(c.updatedAt)}</span>
              </Link>
              <button onClick={() => remove(c.id)} className="invisible p-1.5 text-inkMuted hover:text-fail group-hover:visible"
                aria-label={`${c.title} 삭제`}>
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </nav>
      </aside>

      <section className="flex min-h-0 flex-col rounded-panel border border-line bg-panel">
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-4 py-10 text-center">
              <Bot className="size-8 text-accent" aria-hidden />
              <div>
                <h2 className="text-base font-semibold">AX 산출물 AI 도우미</h2>
                <p className="mt-1 text-sm text-inkMuted">
                  업무 고민을 말해 주면 라이브러리에서 맞는 산출물을 찾아 추천하고 사용법을 알려 드립니다.
                </p>
              </div>
              <div className="grid w-full gap-2 sm:grid-cols-2">
                {STARTERS.map((s) => (
                  <button key={s} onClick={() => send(s)} disabled={busy}
                    className="rounded-panel border border-line px-3 py-2 text-left text-xs text-inkMuted hover:border-accent/60 hover:text-ink">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4">
              {messages.map((m) => <Bubble key={m.id} m={m} />)}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {notice && <p className="border-t border-line px-4 py-1.5 text-xs text-running">{notice}</p>}

        <form
          className="flex items-end gap-2 border-t border-line p-3"
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // 한글 조합 중 Enter 는 글자 확정용이라 보내지 않습니다(마지막 글자가 두 번 가는 문제 방지).
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                send(input)
              }
            }}
            rows={2}
            maxLength={2000}
            placeholder="예) 보고서 초안 쓰는 데 도움 되는 거 있어?  (Enter 전송 · Shift+Enter 줄바꿈)"
            className="min-h-[2.5rem] flex-1 resize-none rounded-panel border border-line bg-panelRaised px-3 py-2 text-sm text-ink placeholder:text-inkMuted/70"
            aria-label="질문 입력"
          />
          {busy ? (
            <Button type="button" variant="outline" onClick={stop} aria-label="중단">
              <Square /> 중단
            </Button>
          ) : (
            <Button type="submit" disabled={!input.trim()} aria-label="보내기">
              <SendHorizontal /> 보내기
            </Button>
          )}
        </form>
        <p className="px-3 pb-2 text-[11px] text-inkMuted/80">
          AI 답변은 틀릴 수 있습니다. 추천된 산출물은 상세 페이지에서 확인하세요.
          {status.data?.model && <span className="font-mono"> · {status.data.model}</span>}
        </p>
      </section>
    </div>
  )
}
