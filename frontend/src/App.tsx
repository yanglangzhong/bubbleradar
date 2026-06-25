import { Suspense, lazy, useEffect, useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import PageLoader from '@/components/shared/PageLoader'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import { useAppStore } from '@/store'
import { authApi } from '@/services/api'

import PwaUpdatePrompt from '@/components/shared/PwaUpdatePrompt'

const Dashboard = lazy(() => import('@/pages/Dashboard'))
const AIBubble = lazy(() => import('@/pages/AIBubble'))
const ChinaRisk = lazy(() => import('@/pages/ChinaRisk'))
const GlobalContagion = lazy(() => import('@/pages/GlobalContagion'))
const CrisisArchive = lazy(() => import('@/pages/CrisisArchive'))
const Crypto = lazy(() => import('@/pages/Crypto'))
const DataLab = lazy(() => import('@/pages/DataLab'))
const Heatmap = lazy(() => import('@/pages/Heatmap'))
const Backtest = lazy(() => import('@/pages/Backtest'))
const Weekly = lazy(() => import('@/pages/Weekly'))
const About = lazy(() => import('@/pages/About'))
const Login = lazy(() => import('@/pages/Login'))

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const { auth, setAuth, clearAuth } = useAppStore()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!auth.token) {
      setReady(true)
      return
    }
    authApi
      .getMe()
      .then((user) => {
        setAuth(auth.token!, user)
      })
      .catch(() => {
        clearAuth()
      })
      .finally(() => setReady(true))
    // 仅在应用挂载时执行一次验证，避免重复请求
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!ready) {
    return <PageLoader />
  }
  return <>{children}</>
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { auth } = useAppStore()
  const location = useLocation()

  if (!auth.isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="ai-bubble" element={<AIBubble />} />
        <Route path="china-risk" element={<ChinaRisk />} />
        <Route path="global" element={<GlobalContagion />} />
        <Route path="archive" element={<CrisisArchive />} />
        <Route path="heatmap" element={<Heatmap />} />
        <Route path="crypto" element={<Crypto />} />
        <Route path="backtest" element={<Backtest />} />
        <Route path="lab" element={<DataLab />} />
        <Route path="weekly" element={<Weekly />} />
        <Route path="about" element={<About />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <AuthInitializer>
          <AppRoutes />
        </AuthInitializer>
      </Suspense>
      <PwaUpdatePrompt />
    </ErrorBoundary>
  )
}

export default App
