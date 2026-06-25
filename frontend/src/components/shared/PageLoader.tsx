import { Activity } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import Skeleton, { SkeletonCard } from './Skeleton'

export default function PageLoader() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6 animate-fade-in p-4">
      <div className="flex items-center gap-3">
        <Activity className="w-6 h-6 text-accent-cyan animate-pulse" />
        <div className="h-8 w-48 bg-bg-surface rounded-lg animate-pulse" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <Skeleton className="h-[320px] w-full rounded-xl" />
      <div className="flex items-center justify-center gap-2 text-xs text-ink-secondary pt-4">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan animate-ping" />
        {t('common.loading')}
      </div>
    </div>
  )
}
