import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Globe, ArrowRight } from 'lucide-react'
import LineChart from '@/components/charts/LineChart'
import Skeleton from '@/components/shared/Skeleton'
import { analyticsApi } from '@/services/api'
import type { LinkageSeries } from '@/services/api'

const SERIES_COLORS = ['#FF2D55', '#FF9500', '#7B61FF']

interface Risk {
  level: string
  title: string
  trigger: string
  impact: string
}

export default function GlobalContagion() {
  const { t } = useTranslation(['globalContagion', 'common'])
  const [linkage, setLinkage] = useState<LinkageSeries | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const risks = t('risks', { returnObjects: true }) as Risk[]

  const load = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const data = await analyticsApi.getGlobalLinkage(30)
      setLinkage(data)
    } catch {
      setError(t('common:error.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    load()
  }, [load])

  const chartSeries = linkage?.series.map((s, i) => ({
    name: s.name,
    data: s.data.map((v) => (v === null ? 0 : v)),
    color: SERIES_COLORS[i % SERIES_COLORS.length],
  })) ?? []

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Globe className="w-6 h-6 text-accent-blue" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {risks.map((risk, i) => (
          <div
            key={i}
            className={`card card-hover border-t-2 ${
              risk.level === 'danger'
                ? 'border-t-accent-red'
                : risk.level === 'warn'
                ? 'border-t-accent-amber'
                : 'border-t-accent-blue'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">{risk.title}</h3>
              <span
                className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${
                  risk.level === 'danger'
                    ? 'bg-accent-red/10 text-accent-red border-accent-red/20'
                    : risk.level === 'warn'
                    ? 'bg-accent-amber/10 text-accent-amber border-accent-amber/20'
                    : 'bg-accent-blue/10 text-accent-blue border-accent-blue/20'
                }`}
              >
                {risk.level.toUpperCase()}
              </span>
            </div>
            <div className="space-y-2 text-xs text-ink-secondary">
              <p className="flex items-center gap-1">
                <ArrowRight className="w-3 h-3 text-ink-muted" />
                {t('trigger')}：{risk.trigger}
              </p>
              <p className="flex items-center gap-1">
                <ArrowRight className="w-3 h-3 text-ink-muted" />
                {t('impact')}：{risk.impact}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold">{t('chartTitle')}</h2>
          {error && (
            <button onClick={load} className="text-xs text-accent-cyan hover:underline">
              {t('common:retry')}
            </button>
          )}
        </div>
        {loading ? (
          <Skeleton className="h-[320px] w-full rounded-xl" />
        ) : (
          <LineChart
            xAxis={linkage?.dates ?? []}
            series={chartSeries}
            height={320}
          />
        )}
        {error && !loading && (
          <p className="mt-2 text-xs text-accent-red">{error}</p>
        )}
        <p className="mt-3 text-[11px] text-ink-muted leading-relaxed">
          {t('footnote')}
        </p>
      </div>
    </div>
  )
}
