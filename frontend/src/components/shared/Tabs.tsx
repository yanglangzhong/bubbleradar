import { useState } from 'react'
import { cn } from '@/utils/cn'

interface Tab {
  id: string
  label: string
}

interface TabsProps {
  tabs: Tab[]
  children: React.ReactNode
  onChange?: (id: string) => void
}

export default function Tabs({ tabs, children, onChange }: TabsProps) {
  const [active, setActive] = useState(tabs[0]?.id)

  const handleClick = (id: string) => {
    setActive(id)
    onChange?.(id)
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleClick(tab.id)}
            className={cn(
              'px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors',
              active === tab.id
                ? 'bg-accent-purple/10 border-accent-purple text-accent-purple'
                : 'border-white/5 text-ink-secondary hover:text-ink-primary hover:border-white/15'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>
        {tabs.map((tab) => (
          <div key={tab.id} className={cn(active === tab.id ? 'block' : 'hidden')}>
            {children}
          </div>
        ))}
      </div>
    </div>
  )
}
