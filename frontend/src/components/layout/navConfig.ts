import {
  Activity,
  BarChart3,
  Brain,
  Globe,
  BookOpen,
  FlaskConical,
  Mail,
  Calendar,
  Bitcoin,
  LineChart,
  Info,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  key: string
  icon: LucideIcon
}

export const navItems: NavItem[] = [
  { to: '/', key: 'home', icon: Activity },
  { to: '/ai-bubble', key: 'aiBubble', icon: Brain },
  { to: '/china-risk', key: 'chinaRisk', icon: BarChart3 },
  { to: '/global', key: 'global', icon: Globe },
  { to: '/archive', key: 'archive', icon: BookOpen },
  { to: '/heatmap', key: 'heatmap', icon: Calendar },
  { to: '/crypto', key: 'crypto', icon: Bitcoin },
  { to: '/backtest', key: 'backtest', icon: LineChart },
  { to: '/lab', key: 'lab', icon: FlaskConical },
  { to: '/weekly', key: 'weekly', icon: Mail },
  { to: '/about', key: 'about', icon: Info },
]
