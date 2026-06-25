export interface CompositeScore {
  ai_bubble_score: number
  china_risk_score: number
  global_risk_score: number
  crypto_risk_score: number
  composite_score: number
  timestamp: string
  source?: string
}

export interface AnalysisStatus {
  status: 'pending' | 'running' | 'ready' | 'error'
  message: string
  scores: {
    ai_bubble: number
    china_risk: number
    global_risk: number
    crypto_risk: number
  }
  composite: CompositeScore
  news: NewsItem[]
  timestamp: string | null
  source_errors?: Record<string, string>
}

export interface HeatmapData {
  dates: string[]
  indicators: { id: number; code: string; name_cn: string; category: string }[]
  matrix: (number | null)[][]
}

export interface Indicator {
  id: number
  code: string
  name_cn: string
  name_en?: string
  category: string
  sub_category?: string
  unit?: string
  source?: string
  update_frequency: string
  description?: string
  thresholds: Record<string, number>
  is_simulated: boolean
  latest_value?: number
  latest_status?: string
  latest_timestamp?: string
  source_url?: string | null
}

export interface IndicatorSnapshot {
  id: number
  indicator_id: number
  value: number
  status: string
  timestamp: string
  meta: Record<string, unknown>
}

export interface NewsItem {
  time: string
  tag: string
  impact: string
  msg: string
  source?: string
  url?: string | null
}

export interface AlertRule {
  id: number
  name: string
  indicator_id?: number
  condition: string
  threshold: number
  severity: string
  is_active: boolean
}

export interface TopSignal {
  title: string
  content: string
  history: string
  source?: string
}

export interface CorrelationNetwork {
  nodes: { id: number; code: string; name: string; category: string; value: number }[]
  edges: { source: number; target: number; value: number }[]
}

export interface HistoricalEvent {
  id: number
  date: string
  title: string
  category?: string
  description?: string
  source?: string
}

export interface DashboardData {
  composite: CompositeScore | null
  history: CompositeScore[]
  ai_indicators: Indicator[]
  china_indicators: Indicator[]
  news: NewsItem[]
  signals: Record<'ai' | 'china' | 'global', TopSignal> | null
  analysis_status: { status: string; message: string }
}
