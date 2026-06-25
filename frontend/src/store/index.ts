import { create } from 'zustand'
import type { CompositeScore, Indicator, NewsItem } from '@/types'

export interface AuthUser {
  id: number
  email: string
  is_active: boolean
  is_superuser: boolean
}

interface AppState {
  composite: CompositeScore | null
  indicators: Record<string, Indicator[]>
  news: NewsItem[]
  lastUpdate: string | null
  auth: {
    user: AuthUser | null
    token: string | null
    isAuthenticated: boolean
  }
  setComposite: (c: CompositeScore) => void
  setIndicators: (category: string, data: Indicator[]) => void
  setNews: (news: NewsItem[]) => void
  setLastUpdate: (t: string) => void
  setAuth: (token: string, user: AuthUser) => void
  clearAuth: () => void
}

const savedToken = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null

export const useAppStore = create<AppState>((set) => ({
  composite: null,
  indicators: {},
  news: [],
  lastUpdate: null,
  auth: {
    user: null,
    token: savedToken,
    isAuthenticated: false,
  },
  setComposite: (composite) => set({ composite }),
  setIndicators: (category, data) => set((state) => ({
    indicators: { ...state.indicators, [category]: data },
  })),
  setNews: (news) => set({ news }),
  setLastUpdate: (lastUpdate) => set({ lastUpdate }),
  setAuth: (token, user) => {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('token', token)
    }
    set({ auth: { token, user, isAuthenticated: true } })
  },
  clearAuth: () => {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('token')
    }
    set({ auth: { token: null, user: null, isAuthenticated: false } })
  },
}))
