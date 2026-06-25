import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import {
  analysisApi,
  compositeApi,
  indicatorsApi,
  newsApi,
  authApi,
  analyticsApi,
  dashboardApi,
} from './api'
import { useAppStore } from '@/store'

const server = setupServer()

describe('API services', () => {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
  afterEach(() => {
    server.resetHandlers()
    useAppStore.setState({ auth: { user: null, token: null, isAuthenticated: false } })
  })
  afterAll(() => server.close())

  describe('analysisApi', () => {
    it('fetches analysis status', async () => {
      server.use(
        http.get('/api/v1/analysis', () =>
          HttpResponse.json({ status: 'ready', message: 'Ready', source_errors: {} })
        )
      )

      const data = await analysisApi.getStatus()
      expect(data.status).toBe('ready')
      expect(data.message).toBe('Ready')
    })

    it('fetches insight', async () => {
      server.use(
        http.get('/api/v1/analysis/insight', () =>
          HttpResponse.json({
            insight: 'Bullish',
            summary: 'Summary',
            model: 'gpt-4',
            notice: 'Disclaimer',
          })
        )
      )

      const data = await analysisApi.getInsight()
      expect(data.insight).toBe('Bullish')
    })
  })

  describe('compositeApi', () => {
    it('fetches latest composite score', async () => {
      server.use(
        http.get('/api/v1/composite', () =>
          HttpResponse.json({
            composite_score: 65,
            ai_bubble_score: 70,
            china_risk_score: 60,
            global_risk_score: 55,
            crypto_risk_score: 50,
            timestamp: new Date().toISOString(),
          })
        )
      )

      const data = await compositeApi.getLatest()
      expect(data.composite_score).toBe(65)
    })

    it('fetches history', async () => {
      server.use(
        http.get('/api/v1/composite/history', ({ request }) => {
          const url = new URL(request.url)
          expect(url.searchParams.get('days')).toBe('7')
          return HttpResponse.json({ history: [{ composite_score: 60, timestamp: '2024-01-01' }] })
        })
      )

      const data = await compositeApi.getHistory(7)
      expect(data).toHaveLength(1)
    })

    it('runs backtest with query params', async () => {
      server.use(
        http.get('/api/v1/composite/backtest', ({ request }) => {
          const url = new URL(request.url)
          expect(url.searchParams.get('days')).toBe('180')
          expect(url.searchParams.get('risk_high')).toBe('70')
          expect(url.searchParams.get('risk_low')).toBe('40')
          return HttpResponse.json({ total_return: { strategy: 12, benchmark: 5 } })
        })
      )

      const data = await compositeApi.backtest()
      expect(data.total_return?.strategy).toBe(12)
    })
  })

  describe('indicatorsApi', () => {
    it('fetches indicators by category', async () => {
      server.use(
        http.get('/api/v1/indicators/category/ai', () =>
          HttpResponse.json([
            {
              id: 1,
              code: 'NVDA_PE',
              name_cn: 'NVDA 市盈率',
              category: 'ai',
              update_frequency: 'daily',
              thresholds: {},
              is_simulated: false,
              latest_value: 55,
            },
          ])
        )
      )

      const data = await indicatorsApi.getByCategory('ai')
      expect(data).toHaveLength(1)
      expect(data[0].name_cn).toBe('NVDA 市盈率')
    })

    it('fetches heatmap', async () => {
      server.use(
        http.get('/api/v1/indicators/heatmap', () => HttpResponse.json({ rows: [], columns: [] }))
      )

      const data = await indicatorsApi.getHeatmap()
      expect(data).toEqual({ rows: [], columns: [] })
    })
  })

  describe('newsApi', () => {
    it('fetches news with limit', async () => {
      server.use(
        http.get('/api/v1/news', ({ request }) => {
          const url = new URL(request.url)
          expect(url.searchParams.get('limit')).toBe('10')
          return HttpResponse.json([{ id: 1, title: 'News' }])
        })
      )

      const data = await newsApi.getNews()
      expect(data).toHaveLength(1)
    })
  })

  describe('authApi', () => {
    it('logs in with form-encoded body', async () => {
      server.use(
        http.post('/api/v1/auth/login', async ({ request }) => {
          const body = await request.text()
          expect(body).toContain('username=admin%40example.com')
          expect(body).toContain('password=admin')
          expect(request.headers.get('Content-Type')).toContain('application/x-www-form-urlencoded')
          return HttpResponse.json({ access_token: 'token', token_type: 'bearer' })
        })
      )

      const data = await authApi.login({ username: 'admin@example.com', password: 'admin' })
      expect(data.access_token).toBe('token')
    })

    it('fetches current user profile', async () => {
      server.use(
        http.get('/api/v1/auth/me', () =>
          HttpResponse.json({ id: 1, email: 'admin@example.com', is_active: true, is_superuser: true })
        )
      )

      const data = await authApi.getMe()
      expect(data.email).toBe('admin@example.com')
    })
  })

  describe('analyticsApi', () => {
    it('fetches China dimensions', async () => {
      server.use(
        http.get('/api/v1/analytics/china/dimensions', () =>
          HttpResponse.json({ labels: ['A'], values: [1], details: [] })
        )
      )

      const data = await analyticsApi.getChinaDimensions()
      expect(data.values).toEqual([1])
    })

    it('fetches global linkage', async () => {
      server.use(
        http.get('/api/v1/analytics/global/linkage', ({ request }) => {
          const url = new URL(request.url)
          expect(url.searchParams.get('days')).toBe('30')
          return HttpResponse.json({ dates: [], series: [] })
        })
      )

      const data = await analyticsApi.getGlobalLinkage()
      expect(data.dates).toEqual([])
    })
  })

  describe('dashboardApi', () => {
    it('sends bearer token from store', async () => {
      useAppStore.setState({
        auth: {
          user: { id: 1, email: 'admin@example.com', is_active: true, is_superuser: true },
          token: 'my-token',
          isAuthenticated: true,
        },
      })

      server.use(
        http.get('/api/v1/dashboard', ({ request }) => {
          expect(request.headers.get('Authorization')).toBe('Bearer my-token')
          return HttpResponse.json({ composite: null, history: [] })
        })
      )

      await dashboardApi.getDashboard()
    })
  })
})