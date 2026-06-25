import { NavLink, useNavigate } from 'react-router-dom'
import { Menu, LogOut, Languages } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import MobileNav from './MobileNav'
import { navItems } from './navConfig'
import { useAppStore } from '@/store'

export default function Header() {
  const [clock, setClock] = useState(new Date())
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const { auth, clearAuth } = useAppStore()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation(['nav', 'common', 'auth'])

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="sticky top-0 z-50 backdrop-blur-2xl bg-bg-deep/90 border-b border-white/5">
      <div className="max-w-[1520px] mx-auto px-4 lg:px-8 h-16 flex items-center justify-between gap-4">
        <NavLink to="/" className="flex items-center gap-2.5 shrink-0">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-cyan opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-accent-cyan"></span>
          </span>
          <span className="font-display font-bold text-lg tracking-tight">{t('app.name')}</span>
        </NavLink>

        <nav className="hidden lg:flex items-center gap-1 overflow-x-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'bg-accent-purple/10 text-accent-purple'
                    : 'text-ink-secondary hover:text-ink-primary hover:bg-white/5'
                }`
              }
            >
              <item.icon className="w-4 h-4" />
              {t(item.key)}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-4 shrink-0">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="lg:hidden p-2 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-white/5 transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
          <time className="font-mono text-xs text-ink-secondary hidden md:block">
            {clock.toLocaleString('zh-CN', { hour12: false })}
          </time>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-red/10 border border-accent-red/20 text-accent-red text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-red animate-pulse" />
            {t('live')}
          </div>
          <button
            onClick={() => i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh')}
            title={i18n.language === 'zh' ? 'Switch to English' : '切换到中文'}
            className="p-2 rounded-lg text-ink-secondary hover:text-ink-primary hover:bg-white/5 transition-colors"
          >
            <Languages className="w-4 h-4" />
          </button>
          {auth.isAuthenticated && (
            <button
              onClick={handleLogout}
              title="退出登录"
              className="p-2 rounded-lg text-ink-secondary hover:text-accent-red hover:bg-white/5 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      <MobileNav open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
    </header>
  )
}
