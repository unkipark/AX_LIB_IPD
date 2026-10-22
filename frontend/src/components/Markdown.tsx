import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/** 설명·설치 가이드 렌더링. raw HTML 은 렌더링하지 않으므로(react-markdown 기본값) XSS 걱정이 없습니다. */
export function Markdown({ children }: { children: string }) {
  if (!children.trim()) return <p className="text-sm text-inkMuted">내용이 없습니다.</p>
  return (
    <div className="markdown text-sm leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  )
}
