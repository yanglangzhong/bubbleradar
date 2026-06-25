import { NavLink, Outlet } from 'react-router-dom'
import { Activity, Brain, BarChart3, Calendar, Info } from 'lucide-react'
import Header from './Header'
import Footer from './Footer'
import MarqueeBar from './MarqueeBar'

const bottomTabs = [
  { to: '/', label: '首页', icon: Activity },
  { to: '/ai-bubble', label: 'AI泡沫', icon: Brain },
  { to: '/china-risk', label: '中国风险', icon: BarChart3 },
  { to: '/heatmap', label: '热力图', icon: Calendar },
  { to: '/about', label: '关于', icon: Info },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <MarqueeBar />
      <main className="flex-1 max-w-[1520px] w-full mx-auto px-4 lg:px-8 py-6 pb-20 lg:pb-0">
        <Outlet />
      </main>
      <Footer />

      {/* Mobile bottom tab bar */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 backdrop-blur-2xl bg-bg-deep/90 border-t border-white/5">
        <div className="flex items-center justify-around h-16">
          {bottomTabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-xs font-medium transition-colors ${
                  isActive
                    ? 'text-accent-purple'
                    : 'text-ink-secondary'
                }`
              }
            >
              <tab.icon className="w-5 h-5" />
              <span>{tab.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
