import { useEffect, useState } from 'react'
import { LineChart as LineChartIcon, Play, RotateCcw, AlertCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import LineChart from '@/components/charts/LineChart'
import { compositeApi } from '@/services/api'
import type { BacktestResult } from '@/services/api'
import { cn } from '@/utils/cn'

export default function Backtest() {
  const { t } = useTranslation(['backtest', 'common'])
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(180)
  const [riskHigh, setRiskHigh] = useState(70)
  const [riskLow, setRiskLow] = useState(40)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await compositeApi.backtest(days, riskHigh, riskLow)
      setResult(data)
    } catch (err) {
      setError(t('common:error.networkError'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    run()
    // 仅在页面挂载时执行一次默认回测
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totalReturn = result?.total_return?.strategy ?? 0
  const totalReturnClass = totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400'
  const totalReturnSign = totalReturn >= 0 ? '+' : ''

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <LineChartIcon className="w-6 h-6 text-accent-cyan" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>
      <p className="text-sm text-ink-secondary">
        {t('subtitle')}
      </p>

      <div className="card">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs text-ink-secondary mb-1">{t('days')}</label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full bg-bg-surface border border-white/10 rounded-lg px-3 py-2 text-sm text-ink-primary"
            >
              <option value={30}>{t('daysOptions.30')}</option>
              <option value={90}>{t('daysOptions.90')}</option>
              <option value={180}>{t('daysOptions.180')}</option>
              <option value={365}>{t('daysOptions.365')}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-ink-secondary mb-1">{t('riskHigh')}</label>
            <input
              type="number"
              min={50}
              max={90}
              value={riskHigh}
              onChange={(e) => setRiskHigh(Number(e.target.value))}
              className="w-full bg-bg-surface border border-white/10 rounded-lg px-3 py-2 text-sm text-ink-primary"
            />
          </div>
          <div>
            <label className="block text-xs text-ink-secondary mb-1">{t('riskLow')}</label>
            <input
              type="number"
              min={10}
              max={50}
              value={riskLow}
              onChange={(e) => setRiskLow(Number(e.target.value))}
              className="w-full bg-bg-surface border border-white/10 rounded-lg px-3 py-2 text-sm text-ink-primary"
            />
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 text-accent-cyan hover:bg-accent-cyan/30 transition-colors disabled:opacity-50"
          >
            {loading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {t('run')}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm bg-accent-red/10 border border-accent-red/20 text-accent-red px-4 py-3 rounded-lg">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <button onClick={run} className="ml-auto text-xs underline hover:no-underline">{t('common:retry')}</button>
        </div>
      )}

      {result && !result.error && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card text-center">
              <div className="text-xs text-ink-secondary mb-1">{t('metrics.totalReturn')}</div>
              <div className={cn('text-2xl font-bold font-display', totalReturnClass)}>
                {`${totalReturnSign}${totalReturn.toFixed(2)}%`}
              </div>
              <div className="text-[10px] text-ink-muted mt-1">
                {t('metrics.benchmark')}: {(result.total_return?.benchmark ?? 0).toFixed(2)}%
              </div>
            </div>
            <div className="card text-center">
              <div className="text-xs text-ink-secondary mb-1">{t('metrics.maxDrawdown')}</div>
              <div className="text-2xl font-bold font-display text-accent-amber">
                {`${(result.max_drawdown?.strategy ?? 0).toFixed(2)}%`}
              </div>
              <div className="text-[10px] text-ink-muted mt-1">
                {t('metrics.benchmark')}: {(result.max_drawdown?.benchmark ?? 0).toFixed(2)}%
              </div>
            </div>
            <div className="card text-center">
              <div className="text-xs text-ink-secondary mb-1">{t('metrics.finalValue')}</div>
              <div className="text-2xl font-bold font-display text-ink-primary">
                {(result.final_value?.strategy ?? 100).toFixed(2)}
              </div>
              <div className="text-[10px] text-ink-muted mt-1">
                {t('metrics.benchmark')}: {(result.final_value?.benchmark ?? 100).toFixed(2)}
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-display font-semibold mb-4">{t('chartTitle')}</h3>
            <LineChart
              xAxis={(result.dates ?? []).filter((_, i) => i % Math.max(1, Math.floor((result.dates ?? []).length / 12)) === 0)}
              series={[
                {
                  name: t('series.strategy'),
                  data: (result.strategy ?? []).filter((_, i) => i % Math.max(1, Math.floor((result.dates ?? []).length / 12)) === 0),
                  color: '#00D4AA',
                },
                {
                  name: t('series.buyHold'),
                  data: (result.benchmark ?? []).filter((_, i) => i % Math.max(1, Math.floor((result.dates ?? []).length / 12)) === 0),
                  color: '#7B61FF',
                },
              ]}
              height={360}
            />
          </div>

          <div className="card bg-accent-cyan/[0.03] border-accent-cyan/20">
            <h3 className="font-display font-semibold text-accent-cyan mb-2">{t('description.title')}</h3>
            <p className="text-sm text-ink-secondary leading-relaxed">
              {t('description.content')}
            </p>
          </div>
        </>
      )}

      {result?.error && (
        <div className="card text-center py-12 text-ink-muted">
          <p>{t('noData.title')}</p>
          <p className="text-xs mt-2">{t('noData.subtitle')}</p>
        </div>
      )}
    </div>
  )
}