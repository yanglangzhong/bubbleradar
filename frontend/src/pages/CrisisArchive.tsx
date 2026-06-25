import { useTranslation } from 'react-i18next'
import { BookOpen } from 'lucide-react'
import CrisisCard from '@/components/cards/CrisisCard'

export default function CrisisArchive() {
  const { t } = useTranslation('crisisArchive')
  const crises = t('crises', { returnObjects: true }) as Array<{ year: string; title: string; lesson: string; compare: string }>

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <BookOpen className="w-6 h-6 text-accent-amber" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>
      <p className="text-sm text-ink-secondary">{t('subtitle')}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {crises.map((c, i) => (
          <CrisisCard key={c.year} {...c} delay={i * 80} />
        ))}
      </div>
    </div>
  )
}
