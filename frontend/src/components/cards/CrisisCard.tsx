interface CrisisCardProps {
  year: string
  title: string
  lesson: string
  compare: string
  delay?: number
}

export default function CrisisCard({ year, title, lesson, compare, delay = 0 }: CrisisCardProps) {
  return (
    <div
      className="card card-hover animate-fade-in"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}
    >
      <div className="flex items-baseline gap-3 mb-2">
        <span className="font-display text-3xl font-bold text-accent-amber">{year}</span>
        <h3 className="text-base font-semibold">{title}</h3>
      </div>
      <p className="text-sm text-ink-secondary leading-relaxed mb-3">{lesson}</p>
      <div className="p-3 rounded-lg bg-accent-red/5 border border-accent-red/10">
        <p className="text-xs text-ink-secondary leading-relaxed">{compare}</p>
      </div>
    </div>
  )
}
