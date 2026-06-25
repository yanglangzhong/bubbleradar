import { cn } from '@/utils/cn'
import type { TopSignal } from '@/types'

interface SignalCardProps {
  title: string
  level: 'danger' | 'warn' | 'watch'
  signal: TopSignal | null
}

const levelStyles = {
  danger: 'border-t-2 border-accent-red bg-accent-red/[0.03]',
  warn: 'border-t-2 border-accent-amber bg-accent-amber/[0.03]',
  watch: 'border-t-2 border-accent-blue bg-accent-blue/[0.03]',
}

const levelBadge = {
  danger: 'bg-accent-red/10 text-accent-red border-accent-red/20',
  warn: 'bg-accent-amber/10 text-accent-amber border-accent-amber/20',
  watch: 'bg-accent-blue/10 text-accent-blue border-accent-blue/20',
}

export default function SignalCard({ title, level, signal }: SignalCardProps) {
  if (!signal) {
    return (
      <div className={cn('card card-hover', levelStyles[level])}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-ink-primary">{title}</h3>
          <span className={cn('text-[10px] px-2 py-0.5 rounded border font-semibold uppercase', levelBadge[level])}>
            {level}
          </span>
        </div>
        <p className="text-sm text-ink-muted leading-relaxed">暂无信号</p>
      </div>
    )
  }

  return (
    <div className={cn('card card-hover', levelStyles[level])}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-ink-primary">{title}</h3>
        <span className={cn('text-[10px] px-2 py-0.5 rounded border font-semibold uppercase', levelBadge[level])}>
          {level}
        </span>
      </div>
      <p className="text-sm text-ink-secondary leading-relaxed mb-3">{signal.content}</p>
      <div className="pt-3 border-t border-white/5">
        <p className="text-xs text-ink-muted leading-relaxed">{signal.history}</p>
      </div>
      {signal.source && (
        <div className="mt-3 pt-2 border-t border-white/5">
          <span className="text-[10px] text-ink-muted bg-white/5 px-1.5 py-0.5 rounded">
            来源：{signal.source}
          </span>
        </div>
      )}
    </div>
  )
}
