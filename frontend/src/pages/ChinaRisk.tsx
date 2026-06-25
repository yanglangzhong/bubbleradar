import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { BarChart3, AlertCircle } from 'lucide-react'
import MetricCard from '@/components/cards/MetricCard'
import RadarChart from '@/components/charts/RadarChart'
import Tabs from '@/components/shared/Tabs'
import Skeleton, { SkeletonCard } from '@/components/shared/Skeleton'
import { indicatorsApi, analyticsApi } from '@/services/api'
import type { ChinaDimensionData } from '@/services/api'
import type { Indicator } from '@/types'

const cardKeys = ['housing', 'debt', 'bank', 'fx', 'real', 'market'] as const

export default function ChinaRisk() {
  const { t } = useTranslation(['chinaRisk', 'common'])

  const detailCards = cardKeys.map((key) => ({
    sub: key,
    title: t(`detailCards.${key}.title`),
    desc: t(`detailCards.${key}.desc`),
  }))

  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [radarData, setRadarData] = useState<ChinaDimensionData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const [inds, dims] = await Promise.all([
        indicatorsApi.getByCategory('china'),
        analyticsApi.getChinaDimensions(),
      ])
      setIndicators(inds)
      setRadarData(dims)
    } catch {
      setError(t('common:error.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-6 h-6 text-accent-vermillion" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold mb-4">{t('chartTitle')}</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {loading && !radarData ? (
            <Skeleton className="h-[360px] w-full rounded-xl" />
          ) : (
            <RadarChart
              data={radarData?.values ?? detailCards.map(() => 0)}
              labels={radarData?.labels ?? detailCards.map((d) => d.title)}
              height={360}
            />
          )}
          <div className="flex flex-col justify-center gap-3">
            {(radarData?.details ?? detailCards.map((d) => ({ label: d.title, value: 0 }))).map((item, idx) => {
              const value = item.value ?? 0
              return (
                <div
                  key={item.label}
                  className="flex items-center justify-between p-3 rounded-lg bg-bg-surface border border-white/5"
                >
                  <span className="text-sm font-medium">{item.label || detailCards[idx]?.title}</span>
                  <span
                    className={`font-mono font-semibold ${
                      value >= 70 ? 'text-accent-red' : value >= 50 ? 'text-accent-amber' : 'text-accent-cyan'
                    }`}
                  >
                    {value}{t('scoreUnit')}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm bg-accent-red/10 border border-accent-red/20 text-accent-red px-4 py-3 rounded-lg">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <button onClick={load} className="ml-auto text-xs underline hover:no-underline">{t('common:retry')}</button>
        </div>
      )}

      <Tabs
        tabs={cardKeys.map((key) => ({
          id: key,
          label: t(`tabs.${key}`),
        }))}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading && indicators.length === 0
            ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
            : indicators
                .filter((ind) => detailCards.find((d) => d.sub === ind.sub_category))
                .map((ind) => <MetricCard key={ind.code} indicator={ind} />)}
        </div>
      </Tabs>
    </div>
  )
}
