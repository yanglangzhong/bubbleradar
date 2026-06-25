import { useEffect, useState } from 'react'
import { cn } from '@/utils/cn'
import { statusColor } from '@/utils/colors'
import { formatNumber } from '@/utils/format'
import { indicatorsApi } from '@/services/api'
import Sparkline from '@/components/charts/Sparkline'
import Skeleton from '@/components/shared/Skeleton'
import type { Indicator, IndicatorSnapshot } from '@/types'

interface MetricCardProps {
  indicator: Indicator
  className?: string
}

const statusGlow = (status?: string) => {
  switch (status) {
    case 'danger':
      return 'shadow-[0_0_20px_rgba(255,45,85,0.12)]'
    case 'warn':
      return 'shadow-[0_0_20px_rgba(255,149,0,0.12)]'
    case 'watch':
      return 'shadow-[0_0_20px_rgba(91,155,213,0.12)]'
    case 'safe':
      return 'shadow-[0_0_20px_rgba(0,212,170,0.12)]'
    default:
      return ''
  }
}

const statusHex = (status?: string) => {
  switch (status) {
    case 'danger':
      return '#FF2D55'
    case 'warn':
      return '#FF9500'
    case 'watch':
      return '#5B9BD5'
    case 'safe':
      return '#00D4AA'
    default:
      return '#8a95b0'
  }
}

export default function MetricCard({ indicator, className }: MetricCardProps) {
  const [history, setHistory] = useState<IndicatorSnapshot[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!indicator.id) {
      setLoading(false)
      return
    }
    indicatorsApi
      .getHistory(indicator.id, 20)
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [indicator.id])

  const values = history.map((s) => s.value)
  const current = indicator.latest_value ?? values[values.length - 1]
  const previous = values.length > 1 ? values[values.length - 2] : undefined
  const change = current !== undefined && previous !== undefined && previous !== 0
    ? ((current - previous) / previous) * 100
    : undefined

  return (
    <div
      className={cn(
        'card card-hover relative overflow-hidden group transition-all duration-300',
        statusGlow(indicator.latest_status),
        className
      )}
    >
      <div
        className={cn(
          'absolute top-0 left-0 w-1 h-full opacity-60 transition-all duration-300 group-hover:opacity-100',
          statusColor(indicator.latest_status).split(' ')[1]
        )}
      />
      <div className="flex items-start justify-between mb-2 pl-3">
        <div className="min-w-0">
          <span className="text-xs text-ink-secondary font-medium block truncate">{indicator.name_cn}</span>
          <div className="flex items-center gap-1.5 mt-1">
            {indicator.is_simulated && (
              <span
                className="inline-block text-[10px] text-accent-amber bg-accent-amber/10 px-1.5 py-0.5 rounded border border-accent-amber/20"
                title="该指标暂无权威实时数据源，当前数值基于历史基线推演，仅供示意参考"
              >
                模拟数据
              </span>
            )}
            {indicator.source && (
              indicator.source_url ? (
                <a
                  href={indicator.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block text-[10px] text-accent-cyan bg-accent-cyan/10 px-1.5 py-0.5 rounded truncate max-w-[140px] hover:underline"
                  title={`点击验证数据来源：${indicator.source}`}
                >
                  来源：{indicator.source}
                </a>
              ) : (
                <span className="inline-block text-[10px] text-ink-muted bg-white/5 px-1.5 py-0.5 rounded truncate max-w-[140px]" title={indicator.source}>
                  来源：{indicator.source}
                </span>
              )
            )}
          </div>
        </div>
        <span
          className={cn(
            'text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border font-semibold shrink-0 ml-2',
            statusColor(indicator.latest_status)
          )}
        >
          {indicator.latest_status || '未知'}
        </span>
      </div>
      <div className="flex items-end justify-between pl-3">
        <div className="font-mono text-2xl font-semibold tracking-tight">
          {formatNumber(current)}
          {indicator.unit && <span className="text-sm text-ink-muted ml-1">{indicator.unit}</span>}
        </div>
        {change !== undefined && (
          <span
            className={cn(
              'text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded',
              change >= 0 ? 'text-accent-red bg-accent-red/10' : 'text-accent-cyan bg-accent-cyan/10'
            )}
          >
            {change >= 0 ? '+' : ''}{change.toFixed(2)}%
          </span>
        )}
      </div>

      <div className="mt-3 pl-3 h-8">
        {loading ? (
          <Skeleton className="h-8 w-full" />
        ) : (
          <Sparkline data={values} color={statusHex(indicator.latest_status)} className="w-full" />
        )}
      </div>

      {indicator.description && (
        <p className="text-[11px] text-ink-muted leading-relaxed mt-3 pt-2 border-t border-white/5 pl-3">
          {indicator.description}
        </p>
      )}
    </div>
  )
}
