import { useEffect, useState } from 'react'
import { newsApi } from '@/services/api'
import type { NewsItem } from '@/types'

const tagClass = (tag: string) => {
  switch (tag) {
    case 'high':
      return 'text-accent-red font-semibold'
    case 'mid':
      return 'text-accent-amber font-semibold'
    default:
      return 'text-accent-cyan'
  }
}

const tagIcon = (tag: string) => {
  switch (tag) {
    case 'high':
      return '🔴'
    case 'mid':
      return '🟡'
    default:
      return '🟢'
  }
}

export default function MarqueeBar() {
  const [items, setItems] = useState<NewsItem[]>([])

  useEffect(() => {
    newsApi.getNews(12).then(setItems).catch(() => {})
  }, [])

  return (
    <div className="bg-bg-surface/70 border-b border-white/5 overflow-hidden whitespace-nowrap py-2">
      <div className="inline-flex animate-marquee">
        {[...items, ...items].map((item, i) => (
          <span key={i} className="mx-6 text-xs font-mono text-ink-secondary">
            <span className={tagClass(item.tag)}>{tagIcon(item.tag)}</span>{' '}
            {item.msg}
          </span>
        ))}
      </div>
    </div>
  )
}
