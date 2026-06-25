import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Calendar, Loader2 } from 'lucide-react'
import { indicatorsApi } from '@/services/api'
import type { HeatmapData } from '@/types'
import { cn } from '@/utils/cn'

const STATUS_COLORS = [
  'bg-emerald-500/20 hover:bg-emerald-500/40', // safe
  'bg-yellow-500/20 hover:bg-yellow-500/40',   // watch
  'bg-orange-500/20 hover:bg-orange-500/40',   // warn
  'bg-red-500/20 hover:bg-red-500/40',         // danger
]

export default function Heatmap() {
  const { t } = useTranslation(['heatmap', 'common'])
  const [data, setData] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)
  const [hovered, setHovered] = useState<{ row: number; col: number } | null>(null)

  const statusLabels = useMemo(
    () => t('statusLabels', { returnObjects: true }) as string[],
    [t]
  )

  useEffect(() => {
    let mounted = true
    setLoading(true)
    indicatorsApi
      .getHeatmap(days)
      .then((d) => mounted && setData(d))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [days])

  const categories = useMemo(() => {
    if (!data) return []
    return Array.from(new Set(data.indicators.map((i) => i.category)))
  }, [data])

  const getCellInfo = (row: number, col: number) => {
    if (!data) return null
    const value = data.matrix[row][col]
    return {
      indicator: data.indicators[row],
      date: data.dates[col],
      value,
      label: value === null ? t('noData') : statusLabels[value],
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-primary flex items-center gap-2">
            <Calendar className="w-6 h-6 text-accent-cyan" />
            {t('title')}
          </h1>
          <p className="text-sm text-ink-secondary mt-1">
            {t('subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[15, 30, 60, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={cn(
                'px-3 py-1.5 text-xs rounded-lg border transition-colors',
                days === d
                  ? 'bg-accent-cyan/20 border-accent-cyan/40 text-accent-cyan'
                  : 'bg-white/5 border-white/10 text-ink-secondary hover:bg-white/10'
              )}
            >
              {d}{t('daysSuffix')}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs">
        {statusLabels.map((label, idx) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={cn('w-3 h-3 rounded-sm', STATUS_COLORS[idx])} />
            <span className="text-ink-secondary">{label}</span>
          </div>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent-cyan" />
        </div>
      )}

      {!loading && data && (
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-surface-secondary/50">
          <div className="min-w-max p-4">
            {categories.map((category) => {
              const rows = data.indicators
                .map((ind, idx) => ({ ...ind, idx }))
                .filter((ind) => ind.category === category)
              if (rows.length === 0) return null

              return (
                <div key={category} className="mb-6 last:mb-0">
                  <h3 className="text-sm font-semibold text-ink-primary mb-2 uppercase tracking-wider">
                    {t(`categories.${category}`, category)}
                  </h3>
                  <div className="space-y-1">
                    {rows.map((ind) => (
                      <div key={ind.code} className="flex items-center gap-1">
                        <div className="w-32 shrink-0 text-xs text-ink-secondary truncate pr-2" title={ind.name_cn}>
                          {ind.name_cn}
                        </div>
                        <div className="flex items-center gap-0.5">
                          {data.dates.map((_, col) => {
                            const value = data.matrix[ind.idx][col]
                            return (
                              <div
                                key={col}
                                className={cn(
                                  'w-3 h-6 rounded-sm transition-all cursor-pointer',
                                  value === null ? 'bg-white/5' : STATUS_COLORS[value]
                                )}
                                onMouseEnter={() => setHovered({ row: ind.idx, col })}
                                onMouseLeave={() => setHovered(null)}
                              />
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}

            <div className="flex items-center gap-1 mt-2 pl-[8.5rem]">
              {data.dates
                .filter((_, i) => i % Math.ceil(data.dates.length / 6) === 0)
                .map((d) => (
                  <div key={d} className="text-[10px] text-ink-tertiary w-8">
                    {d.slice(5)}
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {hovered && data && (
        <div className="fixed bottom-6 right-6 z-50 bg-surface-primary border border-white/10 rounded-lg shadow-xl px-4 py-3 text-sm">
          {(() => {
            const info = getCellInfo(hovered.row, hovered.col)
            if (!info) return null
            return (
              <div className="space-y-1">
                <div className="font-medium text-ink-primary">{info.indicator.name_cn}</div>
                <div className="text-xs text-ink-secondary">{info.date}</div>
                <div className={cn('text-xs font-medium', info.value === null ? 'text-ink-tertiary' : 'text-ink-primary')}>
                  {info.label}
                </div>
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
