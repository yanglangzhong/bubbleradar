import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Brain, AlertCircle } from 'lucide-react'
import MetricCard from '@/components/cards/MetricCard'
import LineChart from '@/components/charts/LineChart'
import Tabs from '@/components/shared/Tabs'
import { indicatorsApi } from '@/services/api'
import type { Indicator } from '@/types'

const generateDates = (count: number) =>
  Array.from({ length: count }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (count - 1 - i))
    return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  })

export default function AIBubble() {
  const { t } = useTranslation(['aiBubble', 'common'])
  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setError(null)
    indicatorsApi.getByCategory('ai').then(setIndicators).catch(() => setError(t('common:error.loadFailed')))
  }, [t])

  useEffect(() => {
    load()
  }, [load])

  const dates = generateDates(30)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Brain className="w-6 h-6 text-accent-purple" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>
      <p className="text-sm text-ink-secondary">{t('subtitle')}</p>

      {error && (
        <div className="flex items-center gap-2 text-sm bg-accent-red/10 border border-accent-red/20 text-accent-red px-4 py-3 rounded-lg">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <button onClick={load} className="ml-auto text-xs underline hover:no-underline">{t('common:retry')}</button>
        </div>
      )}

      <Tabs
        tabs={[
          { id: 'valuation', label: t('tabs.valuation') },
          { id: 'funding', label: t('tabs.funding') },
          { id: 'compute', label: t('tabs.compute') },
          { id: 'sentiment', label: t('tabs.sentiment') },
        ]}
      >
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {indicators.map((ind) => (
              <MetricCard key={ind.code} indicator={ind} />
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-display font-semibold mb-4">{t('charts.pePremium')}</h3>
              <LineChart
                xAxis={dates}
                series={[
                  { name: t('charts.pePremiumRate'), data: dates.map((_, i) => 2.0 + Math.sin(i / 5) * 0.3 + i * 0.01), color: '#7B61FF', area: true },
                  { name: t('charts.historicalAvg'), data: Array(30).fill(1.0), color: '#00D4AA' },
                ]}
              />
            </div>
            <div className="card">
              <h3 className="font-display font-semibold mb-4">{t('charts.mag7')}</h3>
              <LineChart
                xAxis={dates}
                series={[
                  { name: t('charts.mag7Share'), data: dates.map((_, i) => 28 + Math.sin(i / 4) * 4 + i * 0.05), color: '#FF9500', area: true },
                  { name: t('charts.dangerLine'), data: Array(30).fill(35), color: '#FF2D55' },
                ]}
              />
            </div>
          </div>

          <div className="card bg-accent-amber/[0.03] border-accent-amber/20">
            <h3 className="font-display font-semibold text-accent-amber mb-2">{t('story.title')}</h3>
            <p className="text-sm text-ink-secondary leading-relaxed">
              {t('story.content')}
            </p>
          </div>
        </div>
      </Tabs>
    </div>
  )
}
