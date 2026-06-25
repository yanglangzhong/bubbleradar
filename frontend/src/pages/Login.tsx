import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, AlertCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { authApi } from '@/services/api'
import { useAppStore } from '@/store'

export default function Login() {
  const { t } = useTranslation(['login', 'auth'])
  const navigate = useNavigate()
  const { setAuth } = useAppStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const loginRes = await authApi.login({ username: email, password })
      const user = await authApi.getMe()
      setAuth(loginRes.access_token, user)
      navigate('/')
    } catch (err: any) {
      const msg = err.response?.data?.detail || t('error')
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary p-4">
      <div className="w-full max-w-md card space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent-cyan/10 text-accent-cyan">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-display font-bold">{t('title')}</h1>
            <p className="text-xs text-ink-secondary">{t('subtitle')}</p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm bg-accent-red/10 border border-accent-red/20 text-accent-red px-3 py-2 rounded-lg">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs font-medium text-ink-secondary mb-1.5">{t('email')}</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-bg-surface border border-white/10 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus:border-accent-cyan/50"
              placeholder="admin@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-medium text-ink-secondary mb-1.5">{t('password')}</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-bg-surface border border-white/10 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus:border-accent-cyan/50"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-lg text-sm font-medium bg-accent-cyan text-bg-primary hover:bg-accent-cyan/90 transition-colors disabled:opacity-50"
          >
            {loading ? t('loggingIn') : t('submit')}
          </button>
        </form>

        <p className="text-[11px] text-ink-muted text-center">
          {t('defaultAccount')}
        </p>
      </div>
    </div>
  )
}
