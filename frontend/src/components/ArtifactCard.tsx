import { Link } from 'react-router-dom'
import { Paperclip, ThumbsUp } from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { Badge } from '@/components/ui/badge'
import { useMeta } from '@/lib/meta'
import type { ArtifactSummary } from '@/types'

export function ArtifactCard({ a }: { a: ArtifactSummary }) {
  const { typeLabel, toolLabel } = useMeta()
  return (
    <Link
      to={`/artifacts/${a.id}`}
      className="flex flex-col gap-2 rounded-panel border border-line bg-panel p-3 transition-colors hover:border-accent/60 hover:bg-panelRaised"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-inkMuted">{typeLabel(a.type)}</span>
        <StatusBadge status={a.status} />
      </div>
      <h3 className="line-clamp-1 text-sm font-medium text-ink">{a.title}</h3>
      <p className="line-clamp-2 min-h-[2.5rem] text-xs text-inkMuted">{a.summary}</p>
      <div className="flex flex-wrap gap-1">
        {a.tools.map((t) => (
          <Badge key={t} tone="info">{toolLabel(t)}</Badge>
        ))}
        {a.tags.slice(0, 3).map((t) => (
          <Badge key={t}>#{t}</Badge>
        ))}
      </div>
      <div className="mt-auto flex items-center justify-between pt-1 text-xs text-inkMuted">
        <span className="truncate">
          {a.owner.name}
          {a.department && <span className="text-inkMuted/70"> · {a.department}</span>}
        </span>
        <span className="flex shrink-0 items-center gap-2.5 font-mono">
          {a.fileCount > 0 && (
            <span className="flex items-center gap-0.5" title="첨부파일">
              <Paperclip className="size-3" aria-hidden />
              {a.fileCount}
            </span>
          )}
          <span className="flex items-center gap-0.5" title="사용 기록">
            <ThumbsUp className="size-3" aria-hidden />
            {a.useCount}
          </span>
        </span>
      </div>
    </Link>
  )
}
