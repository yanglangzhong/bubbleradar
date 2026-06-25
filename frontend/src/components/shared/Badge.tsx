import { cn } from '@/utils/cn'

interface BadgeProps {
  children: React.ReactNode
  status?: 'safe' | 'watch' | 'warn' | 'danger'
  className?: string
}

export default function Badge({ children, status, className }: BadgeProps) {
  const map = {
    safe: 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20',
    watch: 'bg-accent-blue/10 text-accent-blue border-accent-blue/20',
    warn: 'bg-accent-amber/10 text-accent-amber border-accent-amber/20',
    danger: 'bg-accent-red/10 text-accent-red border-accent-red/20',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border',
        status ? map[status] : 'bg-white/5 text-ink-secondary border-white/10',
        className
      )}
    >
      {children}
    </span>
  )
}
