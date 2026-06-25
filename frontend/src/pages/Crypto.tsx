import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Bitcoin, AlertCircle } from 'lucide-react'
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

export default function Crypto() {
  const { t } = useTranslation(['crypto', 'common'])
  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setError(null)
    indicatorsApi.getByCategory('crypto').then(setIndicators).catch(() => setError(t('common:error.loadFailed')))
  }, [t])

  useEffect(() => {
    load()
  }, [load])

  const dates = generateDates(30)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Bitcoin className="w-6 h-6 text-accent-cyan" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>
      <p className="text-sm text-ink-secondary">
        {t('subtitle')}
      </p>

      {error && (
        <div className="flex items-center gap-2 text-sm bg-accent-red/10 border border-accent-red/20 text-accent-red px-4 py-3 rounded-lg">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <button onClick={load} className="ml-auto text-xs underline hover:no-underline">{t('common:retry')}</button>
        </div>
      )}

      <Tabs
        tabs={[
          { id: 'major', label: t('tabs.major') },
          { id: 'ai', label: t('tabs.ai') },
          { id: 'equity', label: t('tabs.equity') },
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
              <h3 className="font-display font-semibold mb-4">{t('charts.btcRisk')}</h3>
              <LineChart
                xAxis={dates}
                series={[
                  { name: t('charts.btcScore'), data: dates.map((_, i) => 35 + Math.sin(i / 4) * 15 + i * 0.2), color: '#F7931A', area: true },
                  { name: t('charts.dangerLine'), data: Array(30).fill(70), color: '#FF2D55' },
                ]}
              />
            </div>
            <div className="card">
              <h3 className="font-display font-semibold mb-4">{t('charts.aiHeat')}</h3>
              <LineChart
                xAxis={dates}
                series={[
                  { name: t('charts.heatScore'), data: dates.map((_, i) => 55 + Math.sin(i / 3) * 20 + i * 0.3), color: '#7B61FF', area: true },
                  { name: t('charts.warningLine'), data: Array(30).fill(75), color: '#FF9500' },
                ]}
              />
            </div>
          </div>

          <div className="card bg-accent-cyan/[0.03] border-accent-cyan/20">
            <h3 className="font-display font-semibold text-accent-cyan mb-2">{t('notice.title')}</h3>
            <p className="text-sm text-ink-secondary leading-relaxed">
              {t('notice.content')}
            </p>
          </div>
        </div>
      </Tabs>
    </div>
  )
}
