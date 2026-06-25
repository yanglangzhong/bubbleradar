import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FlaskConical, Loader2, Network, BarChart3 } from 'lucide-react'
import HeatmapChart from '@/components/charts/HeatmapChart'
import NetworkChart from '@/components/charts/NetworkChart'
import { analyticsApi } from '@/services/api'
import type { CorrelationResult } from '@/services/api'
import type { CorrelationNetwork } from '@/types'
import { cn } from '@/utils/cn'

const CATEGORIES: { key: string | undefined; i18nKey: string }[] = [
  { key: undefined, i18nKey: 'all' },
  { key: 'ai', i18nKey: 'ai' },
  { key: 'china', i18nKey: 'china' },
  { key: 'global', i18nKey: 'global' },
  { key: 'crypto', i18nKey: 'crypto' },
]

export default function DataLab() {
  const { t } = useTranslation(['dataLab', 'common'])
  const [category, setCategory] = useState<string | undefined>(undefined)
  const [network, setNetwork] = useState<CorrelationNetwork | null>(null)
  const [correlation, setCorrelation] = useState<CorrelationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scenarios = useMemo(
    () => t('backtest.scenarios', { returnObjects: true }) as string[],
    [t]
  )

  const load = useCallback(async (cat?: string) => {
    setLoading(true)
    setError(null)
    try {
      const net = await analyticsApi.getNetwork(cat, 60, 0.45)
      setNetwork(net)
      if (net.nodes.length >= 2) {
        const codes = net.nodes.map((n) => n.code)
        const corr = await analyticsApi.getCorrelation(codes, 60)
        setCorrelation(corr)
      } else {
        setCorrelation(null)
      }
    } catch (e) {
      setError(t('common:error.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    load(category)
  }, [category, load])

  const { labels, matrixData } = useMemo(() => {
    if (!correlation) return { labels: [], matrixData: [] as number[][] }
    const labels = correlation.codes
    const matrixData = labels.map((row) => labels.map((col) => correlation.matrix[row][col]))
    return { labels, matrixData }
  }, [correlation])

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <FlaskConical className="w-6 h-6 text-accent-purple" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>
      <p className="text-sm text-ink-secondary">{t('subtitle')}</p>

      <div className="flex flex-wrap items-center gap-2">
        {CATEGORIES.map((c) => (
          <button
            key={c.key ?? 'all'}
            onClick={() => setCategory(c.key)}
            className={cn(
              'px-3 py-1.5 text-xs rounded-lg border transition-colors',
              category === c.key
                ? 'bg-accent-purple/20 border-accent-purple/40 text-accent-purple'
                : 'bg-white/5 border-white/10 text-ink-secondary hover:bg-white/10'
            )}
          >
            {t(`categories.${c.i18nKey}`)}
          </button>
        ))}
        {loading && <Loader2 className="w-4 h-4 animate-spin text-accent-purple ml-2" />}
      </div>

      {error && (
        <div className="text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 px-3 py-2 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Network className="w-4 h-4 text-accent-cyan" />
            <h2 className="font-display font-semibold">{t('charts.network')}</h2>
          </div>
          {network && network.nodes.length >= 2 ? (
            <NetworkChart nodes={network.nodes} edges={network.edges} height={380} />
          ) : (
            <div className="flex flex-col items-center justify-center h-[380px] text-ink-muted text-sm">
              {loading ? <Loader2 className="w-6 h-6 animate-spin text-accent-cyan mb-2" /> : <Network className="w-8 h-8 mb-2 opacity-40" />}
              <p>{loading ? t('charts.networkLoading') : t('charts.networkNoData')}</p>
            </div>
          )}
          <p className="text-[11px] text-ink-muted mt-2">
            {t('charts.networkHint')}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-accent-purple" />
            <h2 className="font-display font-semibold">{t('charts.matrix')}</h2>
          </div>
          {labels.length >= 2 ? (
            <HeatmapChart labels={labels} data={matrixData} height={380} />
          ) : (
            <div className="flex flex-col items-center justify-center h-[380px] text-ink-muted text-sm">
              {loading ? <Loader2 className="w-6 h-6 animate-spin text-accent-purple mb-2" /> : <BarChart3 className="w-8 h-8 mb-2 opacity-40" />}
              <p>{loading ? t('charts.matrixLoading') : t('charts.matrixNoData')}</p>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="font-display font-semibold mb-4">{t('backtest.title')}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {scenarios.map((date) => (
            <button
              key={date}
              className="text-left px-4 py-2 rounded-lg bg-bg-surface border border-white/5 text-sm text-ink-secondary hover:border-accent-amber/30 hover:text-ink-primary transition-colors"
            >
              {date}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-ink-muted">{t('backtest.hint')}</p>
      </div>
    </div>
  )
}
