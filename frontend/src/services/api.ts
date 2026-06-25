import axios from 'axios'
import { useAppStore } from '@/store'
import type { CompositeScore, Indicator, IndicatorSnapshot, NewsItem, AlertRule, TopSignal, AnalysisStatus, HeatmapData, CorrelationNetwork, HistoricalEvent, DashboardData } from '@/types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = useAppStore.getState().auth.token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAppStore.getState().clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface InsightResponse {
  insight: string
  summary: string
  model: string
  notice: string
}

export interface CorrelationResult {
  codes: string[]
  matrix: Record<string, Record<string, number>>
  points: number
}

export const analysisApi = {
  getStatus: () => api.get<AnalysisStatus>('/analysis').then((r) => r.data),
  refresh: () => api.post<AnalysisStatus>('/analysis/refresh').then((r) => r.data),
  getInsight: () => api.get<InsightResponse>('/analysis/insight').then((r) => r.data),
}

export interface BacktestResult {
  dates?: string[]
  benchmark?: number[]
  strategy?: number[]
  total_return?: { benchmark: number; strategy: number }
  max_drawdown?: { benchmark: number; strategy: number }
  final_value?: { benchmark: number; strategy: number }
  parameters?: { days: number; risk_high: number; risk_low: number }
  error?: string
}

export const compositeApi = {
  getLatest: () => api.get<CompositeScore>('/composite').then(r => r.data),
  getHistory: (days = 30) => api.get<{ history: CompositeScore[] }>(`/composite/history?days=${days}`).then(r => r.data.history),
  recalculate: () => api.post<CompositeScore>('/composite/recalculate').then(r => r.data),
  backtest: (days = 180, riskHigh = 70, riskLow = 40) =>
    api.get<BacktestResult>(`/composite/backtest?days=${days}&risk_high=${riskHigh}&risk_low=${riskLow}`).then(r => r.data),
}

export const indicatorsApi = {
  getByCategory: (category: string, subCategory?: string) =>
    api.get<Indicator[]>(`/indicators/category/${category}`, { params: { sub_category: subCategory } }).then(r => r.data),
  getHistory: (id: number, limit = 90) =>
    api.get<IndicatorSnapshot[]>(`/indicators/${id}/history?limit=${limit}`).then(r => r.data),
  getHeatmap: (days = 30) =>
    api.get<HeatmapData>(`/indicators/heatmap?days=${days}`).then(r => r.data),
}

export const newsApi = {
  getNews: (limit = 10) => api.get<NewsItem[]>(`/news?limit=${limit}`).then(r => r.data),
  getTopSignals: () => api.get<Record<'ai' | 'china' | 'global', TopSignal>>('/news/signals/top').then(r => r.data),
}

export const alertsApi = {
  getRules: () => api.get<AlertRule[]>('/alerts/rules').then(r => r.data),
  getEvents: () => api.get('/alerts/events').then(r => r.data),
  check: () => api.post('/alerts/check').then(r => r.data),
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserProfile {
  id: number
  email: string
  is_active: boolean
  is_superuser: boolean
}

export const authApi = {
  login: (credentials: LoginCredentials) => {
    const params = new URLSearchParams()
    params.append('username', credentials.username)
    params.append('password', credentials.password)
    return api.post<LoginResponse>('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }).then(r => r.data)
  },
  getMe: () => api.get<UserProfile>('/auth/me').then(r => r.data),
}

export interface ChinaDimensionData {
  labels: string[]
  values: number[]
  details: { key: string; label: string; value: number }[]
}

export interface LinkageSeries {
  dates: string[]
  series: { name: string; data: (number | null)[]; unit: string }[]
}

export const analyticsApi = {
  getEvents: (category?: string, limit = 50) =>
    api.get<HistoricalEvent[]>('/analytics/events', { params: { category, limit } }).then(r => r.data),
  getNetwork: (category?: string, days = 60, threshold = 0.5) =>
    api.get<CorrelationNetwork>('/analytics/network', { params: { category, days, threshold } }).then(r => r.data),
  getCorrelation: (codes: string[], days = 60) =>
    api.post<CorrelationResult>('/analytics/indicators/correlation', { codes, days }).then(r => r.data),
  getChinaDimensions: () => api.get<ChinaDimensionData>('/analytics/china/dimensions').then(r => r.data),
  getGlobalLinkage: (days = 30) => api.get<LinkageSeries>('/analytics/global/linkage', { params: { days } }).then(r => r.data),
}

export const dashboardApi = {
  getDashboard: () => api.get<DashboardData>('/dashboard').then(r => r.data),
}

export default api
