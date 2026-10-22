import * as React from 'react'
import { cn } from '@/lib/utils'

/** 입력 계열 공통 스타일. 네이티브 요소를 그대로 써서 폐쇄망에서 추가 의존성이 없습니다. */
export const fieldClass =
  'w-full rounded-panel border border-line bg-panelRaised px-2.5 text-sm text-ink placeholder:text-inkMuted/70 disabled:opacity-40'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input ref={ref} className={cn(fieldClass, 'h-8', className)} {...props} />
)
Input.displayName = 'Input'

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea ref={ref} className={cn(fieldClass, 'min-h-24 py-2 font-mono text-xs leading-relaxed', className)} {...props} />
  )
)
Textarea.displayName = 'Textarea'

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => <select ref={ref} className={cn(fieldClass, 'h-8 px-2', className)} {...props} />
)
Select.displayName = 'Select'

export function Field({
  label,
  hint,
  required,
  children,
  className,
}: {
  label: string
  hint?: string
  required?: boolean
  children: React.ReactNode
  className?: string
}) {
  return (
    <label className={cn('flex flex-col gap-1', className)}>
      <span className="text-xs font-medium text-inkMuted">
        {label}
        {required && <span className="ml-0.5 text-fail">*</span>}
      </span>
      {children}
      {hint && <span className="text-[11px] text-inkMuted/80">{hint}</span>}
    </label>
  )
}
