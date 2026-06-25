import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Activity, TrendingUp, AlertTriangle, Globe, Newspaper, RefreshCw, AlertCircle, Database, Sparkles, Calendar } from 'lucide-react'
import GaugeChart from '@/components/charts/GaugeChart'
import LineChart from '@/components/charts/LineChart'
import SignalCard from '@/components/cards/SignalCard'
import MetricCard from '@/components/cards/MetricCard'
import Badge from '@/components/shared/Badge'
import Skeleton, { SkeletonCard } from '@/components/shared/Skeleton'
import { analysisApi, compositeApi, indicatorsApi, newsApi, analyticsApi, dashboardApi } from '@/services/api'
import type { InsightResponse } from '@/services/api'
import { useDashboardWebSocket } from '@/hooks/useWebSocket'
import { useAppStore } from '@/store'
import { scoreStatus, scoreText } from '@/utils/colors'
import { cn } from '@/utils/cn'
import type { CompositeScore, DashboardData, HistoricalEvent, Indicator, TopSignal } from '@/types'

export default function Dashboard() {
  const { t } = useTranslation(['dashboard', 'common'])
  const { composite, setComposite, setIndicators, news, setNews, lastUpdate, setLastUpdate } = useAppStore()
  const [aiIndicators, setAiIndicators] = useState<Indicator[]>([])
  const [chinaIndicators, setChinaIndicators] = useState<Indicator[]>([])
  const [history, setHistory] = useState<CompositeScore[]>([])
  const [signals, setSignals] = useState<Record<'ai' | 'china' | 'global', TopSignal> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analysisStatus, setAnalysisStatus] = useState<{ status: string; message: string } | null>(null)
  const [sourceErrors, setSourceErrors] = useState<Record<string, string>>({})
  const [insight, setInsight] = useState<InsightResponse | null>(null)
  const [events, setEvents] = useState<HistoricalEvent[]>([])

  const applyDashboardData = useCallback((dash: DashboardData, background = false) => {
    if (!background) setLoading(true)
    setError(null)

    if (dash.analysis_status) {
      setAnalysisStatus({ status: dash.analysis_status.status, message: dash.analysis_status.message })
    }
    if (dash.composite) {
      setComposite(dash.composite)
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    }
    if (dash.history?.length) setHistory(dash.history)
    if (dash.ai_indicators?.length) {
      setAiIndicators(dash.ai_indicators)
      setIndicators('ai', dash.ai_indicators)
    }
    if (dash.china_indicators?.length) {
      setChinaIndicators(dash.china_indicators)
      setIndicators('china', dash.china_indicators)
    }
    if (dash.news?.length) setNews(dash.news)
    if (dash.signals) setSignals(dash.signals)

    // Fetch insight separately (not included in aggregated endpoint)
    analysisApi.getInsight().then(setInsight).catch(() => {})

    if (!background) setLoading(false)
  }, [setComposite, setIndicators, setLastUpdate, setNews])

  const { connected: wsConnected } = useDashboardWebSocket({
    onSnapshot: (dash) => applyDashboardData(dash),
    onUpdate: (dash) => applyDashboardData(dash, true),
  })

  useEffect(() => {
    analyticsApi.getEvents(undefined, 20).then(setEvents).catch(() => setEvents([]))
  }, [])

  const load = useCallback(async (background = false) => {
    if (!background) setLoading(true)
    setError(null)

    // Try aggregated endpoint first
    try {
      const dash = await dashboardApi.getDashboard()
      applyDashboardData(dash, background)
      return
    } catch (e) {
      console.warn('Dashboard aggregated endpoint failed, falling back to individual calls', e)
    }

    // Fallback: original 8 parallel calls
    const results = await Promise.allSettled([
      analysisApi.getStatus(),
      compositeApi.getLatest(),
      compositeApi.getHistory(7),
      indicatorsApi.getByCategory('ai'),
      indicatorsApi.getByCategory('china'),
      newsApi.getNews(8),
      newsApi.getTopSignals(),
      analysisApi.getInsight(),
    ] as const)

    const [analysis, comp, hist, ai, china, newsData, sigs, insightRes] = results

    if (analysis.status === 'fulfilled') {
      setAnalysisStatus({ status: analysis.value.status, message: analysis.value.message })
      setSourceErrors(analysis.value.source_errors || {})
      if (analysis.value.status === 'ready' && analysis.value.composite) {
        setComposite(analysis.value.composite)
        setNews(analysis.value.news)
        setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
      }
    }
    if (comp.status === 'fulfilled') {
      setComposite(comp.value)
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    }
    if (hist.status === 'fulfilled') setHistory(hist.value)
    if (ai.status === 'fulfilled') {
      setAiIndicators(ai.value)
      setIndicators('ai', ai.value)
    }
    if (china.status === 'fulfilled') {
      setChinaIndicators(china.value)
      setIndicators('china', china.value)
    }
    if (newsData.status === 'fulfilled') setNews(newsData.value)
    if (sigs.status === 'fulfilled') setSignals(sigs.value)
    if (insightRes.status === 'fulfilled') setInsight(insightRes.value)

    const failed = results.filter((r) => r.status === 'rejected').length
    if (failed > 0) {
      setError(t('common:error.partialLoadFailed'))
    }

    if (!background) setLoading(false)
  }, [applyDashboardData, setComposite, setIndicators, setLastUpdate, setNews, t])

  useEffect(() => {
    // 初始加载：WebSocket 连接后会推送快照，但为防止 WS 不可用仍主动请求一次
    load()
  }, [load])

  const status = composite ? scoreStatus(composite.composite_score) : 'safe'

  const chartEvents = useMemo(() => {
    const dates = history.map((h) =>
      new Date(h.timestamp).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
    )
    return events
      .map((e) => ({
        date: new Date(e.date).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }),
        title: e.title,
        category: e.category,
      }))
      .filter((e) => dates.includes(e.date))
  }, [history, events])

  const sourceStats = useMemo(() => {
    const all = [...aiIndicators, ...chinaIndicators]
    const map = new Map<string, number>()
    all.forEach((ind) => {
      const s = ind.source || '未知'
      map.set(s, (map.get(s) || 0) + 1)
    })
    if (composite?.source) {
      map.set(composite.source, (map.get(composite.source) || 0) + 1)
    }
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  }, [aiIndicators, chinaIndicators, composite])

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold flex items-center gap-2">
            <Activity className="w-6 h-6 text-accent-cyan" />
            {t('title')}
          </h1>
          <p className="text-sm text-ink-secondary mt-1 flex items-center gap-3 flex-wrap">
            <span>{t('formula')}</span>
            {lastUpdate && (
              <>
                <span className="font-mono text-ink-muted">{t('updatedAt')} {lastUpdate}</span>
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-full border',
                    wsConnected
                      ? 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20'
                      : 'text-accent-amber bg-accent-amber/10 border-accent-amber/20'
                  )}
                >
                  <span className="relative flex h-1.5 w-1.5">
                    {wsConnected && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-cyan opacity-75"></span>
                    )}
                    <span
                      className={cn(
                        'relative inline-flex rounded-full h-1.5 w-1.5',
                        wsConnected ? 'bg-accent-cyan' : 'bg-accent-amber'
                      )}
                    ></span>
                  </span>
                  {wsConnected ? t('wsConnected') : t('wsDisconnected')}
                </span>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {error && (
            <div className="hidden sm:flex flex-col gap-1 text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 px-3 py-1.5 rounded-lg max-w-md">
              <div className="flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                {error}
              </div>
              {Object.keys(sourceErrors).length > 0 && (
                <div className="pl-5 text-[10px] opacity-80">
                  {t('common:failedSources')}：{Object.keys(sourceErrors).join('、')}
                </div>
              )}
            </div>
          )}
          <button
            onClick={() => load()}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
            {t('refresh')}
          </button>
          <Badge status={status as any} className="text-sm px-3 py-1">
            {composite ? scoreText(composite.composite_score) : t('common:status.loading')}
          </Badge>
        </div>
      </div>

      {error && (
        <div className="sm:hidden flex flex-col gap-1 text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 px-3 py-2 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
          {Object.keys(sourceErrors).length > 0 && (
            <div className="pl-6 text-[10px] opacity-80">
              {t('common:failedSources')}：{Object.keys(sourceErrors).join('、')}
            </div>
          )}
        </div>
      )}

      {analysisStatus && analysisStatus.status !== 'ready' && (
        <div className="flex items-center gap-3 text-sm bg-accent-cyan/10 border border-accent-cyan/20 text-accent-cyan px-4 py-3 rounded-lg">
          <RefreshCw className={cn('w-4 h-4', analysisStatus.status === 'running' && 'animate-spin')} />
          <div className="flex-1">
            <span className="font-medium">{analysisStatus.message}</span>
            <p className="text-xs text-ink-secondary mt-0.5">{t('analysis.running')}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold">{t('sections.categoryScores')}</h2>
            <span className="text-xs text-ink-muted font-mono">COMPOSITE RISK</span>
          </div>
          {loading && !composite ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Skeleton className="h-[160px] rounded-full mx-auto w-[160px]" />
              <Skeleton className="h-[160px] rounded-full mx-auto w-[160px]" />
              <Skeleton className="h-[160px] rounded-full mx-auto w-[160px]" />
              <Skeleton className="h-[160px] rounded-full mx-auto w-[160px]" />
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <GaugeChart
                  value={composite?.ai_bubble_score ?? 0}
                  name={t('category.ai')}
                  color="#7B61FF"
                  height={160}
                />
                <div className="text-sm font-medium text-accent-purple mt-2">{t('category.ai')}</div>
              </div>
              <div className="text-center">
                <GaugeChart
                  value={composite?.china_risk_score ?? 0}
                  name={t('category.china')}
                  color="#C41E3A"
                  height={160}
                />
                <div className="text-sm font-medium text-accent-vermillion mt-2">{t('category.china')}</div>
              </div>
              <div className="text-center">
                <GaugeChart
                  value={composite?.global_risk_score ?? 0}
                  name={t('category.global')}
                  color="#00D4AA"
                  height={160}
                />
                <div className="text-sm font-medium text-accent-cyan mt-2">{t('category.global')}</div>
              </div>
              <div className="text-center">
                <GaugeChart
                  value={composite?.crypto_risk_score ?? 0}
                  name={t('category.crypto')}
                  color="#F7931A"
                  height={160}
                />
                <div className="text-sm font-medium text-[#F7931A] mt-2">{t('category.crypto')}</div>
              </div>
            </div>
          )}
          <div className="mt-4 text-center text-xs text-ink-muted">
            <span className="text-accent-cyan">● {t('scoreRange.safe')}</span>
            <span className="ml-4 text-accent-blue">● {t('scoreRange.watch')}</span>
            <span className="ml-4 text-accent-amber">● {t('scoreRange.warning')}</span>
            <span className="ml-4 text-accent-red">● {t('scoreRange.danger')}</span>
          </div>
          {composite?.source && (
            <div className="mt-2 text-center text-[10px] text-ink-muted">
              {t('common:source')}：{composite.source}
            </div>
          )}
        </div>

        <div className="card flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Newspaper className="w-4 h-4 text-accent-amber" />
            <h2 className="font-display font-semibold">{t('sections.latestNews')}</h2>
          </div>
          <div className="flex-1 overflow-y-auto space-y-2 max-h-[360px] pr-1">
            {loading && news.length === 0 ? (
              Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))
            ) : news.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-ink-muted">
                <Newspaper className="w-8 h-8 mb-2 opacity-40" />
                <p className="text-xs">{t('news.empty')}</p>
                <p className="text-[10px] mt-1 opacity-60">{t('news.loading')}</p>
              </div>
            ) : (
              news.map((item, i) => (
                <div
                  key={i}
                  className={`flex flex-col gap-1 p-2 rounded-lg text-xs bg-bg-surface border-l-2 ${
                    item.impact === 'impact-high'
                      ? 'border-accent-red'
                      : item.impact === 'impact-mid'
                      ? 'border-accent-amber'
                      : 'border-accent-cyan'
                  }`}
                >
                  <div className="flex gap-2">
                    <span className="font-mono text-ink-muted shrink-0">{item.time}</span>
                    {item.url ? (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-ink-secondary leading-relaxed hover:text-accent-cyan hover:underline"
                        title={t('news.openOriginal')}
                      >
                        {item.msg}
                      </a>
                    ) : (
                      <span className="text-ink-secondary leading-relaxed">{item.msg}</span>
                    )}
                  </div>
                  {item.source && (
                    <div className="pl-8">
                      {item.url ? (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block text-[10px] text-accent-cyan bg-accent-cyan/10 px-1.5 py-0.5 rounded hover:underline"
                          title={t('news.verifyOriginal')}
                        >
                          {t('news.source')}：{item.source}
                        </a>
                      ) : (
                        <span className="inline-block text-[10px] text-ink-muted bg-white/5 px-1.5 py-0.5 rounded">
                          {t('news.source')}：{item.source}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {insight && (
        <div className="card bg-gradient-to-br from-accent-purple/5 to-accent-cyan/5 border-accent-purple/10">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-accent-purple" />
            <h2 className="font-display font-semibold">{t('sections.insight')}</h2>
            <span className="text-[10px] text-ink-muted ml-auto">{insight.model}</span>
          </div>
          <p className="text-sm text-ink-primary leading-relaxed">{insight.insight}</p>
          <p className="text-xs text-ink-secondary mt-2 flex items-center gap-1.5">
            <Newspaper className="w-3 h-3" />
            {t('insightLabels.sentiment')}：{insight.summary}
          </p>
          {insight.notice && (
            <p className="text-[10px] text-ink-muted mt-2 bg-white/5 px-2 py-1 rounded inline-block">
              {insight.notice}
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading && !signals
          ? Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)
          : signals && (signals.ai || signals.china || signals.global) ? (
              <>
                {signals.ai && <SignalCard title={t('signals.ai')} level="warn" signal={signals.ai} />}
                {signals.china && <SignalCard title={t('signals.china')} level="warn" signal={signals.china} />}
                {signals.global && <SignalCard title={t('signals.global')} level="watch" signal={signals.global} />}
              </>
            ) : (
              <div className="card md:col-span-3 flex items-center justify-center py-8 text-ink-muted">
                <AlertTriangle className="w-6 h-6 mr-2 opacity-40" />
                <span className="text-sm">{t('signals.empty')}</span>
              </div>
            )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-accent-cyan" />
              {t('sections.historicalChart')}
            </h2>
          </div>
          {loading && history.length === 0 ? (
            <Skeleton className="h-[260px] w-full rounded-xl" />
          ) : (
            <LineChart
              xAxis={history.map((h) => new Date(h.timestamp).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }))}
              series={[
                { name: t('chartSeries.composite'), data: history.map((h) => h.composite_score), color: '#FF9500', area: true },
                { name: t('category.ai'), data: history.map((h) => h.ai_bubble_score), color: '#7B61FF' },
                { name: t('category.china'), data: history.map((h) => h.china_risk_score), color: '#C41E3A' },
                { name: t('category.global'), data: history.map((h) => h.global_risk_score), color: '#00D4AA' },
                { name: t('category.crypto'), data: history.map((h) => h.crypto_risk_score), color: '#F7931A' },
              ]}
              events={chartEvents}
              height={260}
            />
          )}
        </div>
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-accent-amber" />
              {t('subsections.subIndices')}
            </h2>
          </div>
          {loading && aiIndicators.length === 0 ? (
            <Skeleton className="h-[260px] w-full rounded-xl" />
          ) : (
            <LineChart
              xAxis={history.map((h) => new Date(h.timestamp).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }))}
              series={[
                {
                  name: t('chartSeries.aiSentiment'),
                  data: history.map(() => aiIndicators.find((i) => i.code === 'ai_sentiment')?.latest_value ?? 0),
                  color: '#7B61FF',
                },
                {
                  name: t('chartSeries.housing'),
                  data: history.map(() => chinaIndicators.find((i) => i.code === 'housing')?.latest_value ?? 0),
                  color: '#C41E3A',
                },
              ]}
              height={260}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Globe className="w-4 h-4 text-accent-purple" />
            <h2 className="font-display font-semibold">{t('subsections.aiCore')}</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {loading && aiIndicators.length === 0
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
              : aiIndicators.map((ind) => <MetricCard key={ind.code} indicator={ind} />)}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-accent-vermillion" />
            <h2 className="font-display font-semibold">{t('subsections.chinaCore')}</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {loading && chinaIndicators.length === 0
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
              : chinaIndicators.map((ind) => <MetricCard key={ind.code} indicator={ind} />)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2">
          <div className="flex items-center gap-2 mb-3">
            <Database className="w-4 h-4 text-accent-cyan" />
            <h2 className="font-display font-semibold">{t('subsections.sources')}</h2>
            <span className="ml-auto inline-flex items-center gap-1.5 text-[11px] text-accent-cyan bg-accent-cyan/10 px-2 py-0.5 rounded-full border border-accent-cyan/20">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-cyan opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-cyan"></span>
              </span>
              {t('subsections.live')}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {sourceStats.length === 0 ? (
              <span className="text-xs text-ink-muted">{t('sourceStats.loading')}</span>
            ) : (
              sourceStats.map(([source, count]) => {
                const isBaseline =
                  source.includes(t('sourceStats.baseline')) ||
                  source.includes(t('sourceStats.simulated')) ||
                  source.includes(t('sourceStats.inferred'))
                const isAuthority = ['FRED', 'Yahoo Finance', 'Alpha Vantage', 'AkShare'].some((k) => source.includes(k))
                return (
                  <span
                    key={source}
                    className={cn(
                      'text-[11px] px-2 py-1 rounded border',
                      isBaseline
                        ? 'bg-accent-amber/10 text-accent-amber border-accent-amber/20'
                        : isAuthority
                        ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20'
                        : 'bg-white/5 text-ink-secondary border-white/10'
                    )}
                    title={t('sourceStats.tooltip', { count, source })}
                  >
                    {source} ×{count}
                  </span>
                )
              })
            )}
          </div>
          <p className="text-[11px] text-ink-muted mt-3 leading-relaxed">
            {t('fallbackDesc')}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-4 h-4 text-accent-amber" />
            <h2 className="font-display font-semibold">{t('subsections.authority')}</h2>
          </div>
          <ul className="space-y-2 text-[11px] text-ink-secondary">
            {(t('authorityNotes', { returnObjects: true }) as string[]).map((note, idx, arr) => (
              <li key={idx} className="flex items-start gap-2">
                <span className={cn('mt-0.5', idx === arr.length - 1 ? 'text-accent-amber' : 'text-accent-cyan')}>●</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {events.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-4 h-4 text-accent-amber" />
            <h2 className="font-display font-semibold">{t('subsections.events')}</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {events.slice(0, 10).map((e) => (
              <span
                key={e.id}
                className="text-[11px] px-2 py-1 rounded border bg-white/5 border-white/10 text-ink-secondary"
                title={e.description}
              >
                {e.date} {e.title}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
