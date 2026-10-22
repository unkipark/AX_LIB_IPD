import { Badge } from '@/components/ui/badge'
import { useMeta } from '@/lib/meta'

const TONE: Record<string, 'neutral' | 'running' | 'info' | 'ok'> = {
  idea: 'neutral',
  developing: 'running',
  pilot: 'info',
  deployed: 'ok',
  retired: 'neutral',
}

export function StatusBadge({ status }: { status: string }) {
  const { statusLabel } = useMeta()
  return <Badge tone={TONE[status] ?? 'neutral'}>{statusLabel(status)}</Badge>
}
