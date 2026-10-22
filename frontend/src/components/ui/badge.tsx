import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-panel border px-1.5 py-0.5 text-xs font-medium',
  {
    variants: {
      tone: {
        neutral: 'border-line bg-panelRaised text-inkMuted',
        running: 'border-running/40 bg-running/10 text-running',
        ok: 'border-ok/40 bg-ok/10 text-ok',
        fail: 'border-fail/40 bg-fail/10 text-fail',
        info: 'border-series1/40 bg-series1/10 text-series1',
      },
    },
    defaultVariants: { tone: 'neutral' },
  }
)

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
