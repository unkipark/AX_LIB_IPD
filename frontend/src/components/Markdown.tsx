import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import remarkGfm from 'remark-gfm'

/** 설명·설치 가이드·AI 도우미 답변 렌더링. raw HTML 은 렌더링하지 않으므로(react-markdown 기본값) XSS 걱정이 없습니다.
 *  /artifacts/12 같은 앱 내부 링크는 새로고침 없이 이동하고, 외부 링크는 새 탭으로 엽니다. */
export function Markdown({ children, empty = '내용이 없습니다.' }: { children: string; empty?: string }) {
  if (!children.trim()) return <p className="text-sm text-inkMuted">{empty}</p>
  return (
    <div className="markdown text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href = '', children: text }) =>
            href.startsWith('/') && !href.startsWith('//') ? (
              <Link to={href}>{text}</Link>
            ) : (
              <a href={href} target="_blank" rel="noreferrer">{text}</a>
            ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
