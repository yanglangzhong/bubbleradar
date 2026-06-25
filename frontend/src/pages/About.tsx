import { Info, Shield, Scale, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function About() {
  const { t } = useTranslation('about')
  const limitations = t('limitations.items', { returnObjects: true }) as string[]
  const frequencyKeys = ['daily', 'weekly', 'monthly'] as const
  const frequencyColors = ['text-accent-cyan', 'text-accent-amber', 'text-accent-purple']

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Info className="w-6 h-6 text-accent-cyan" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="w-5 h-5 text-accent-cyan" />
            <h2 className="font-display font-semibold">{t('stance.title')}</h2>
          </div>
          <p className="text-sm text-ink-secondary leading-relaxed">
            {t('stance.content')}
          </p>
          <blockquote className="mt-4 pl-4 border-l-2 border-accent-purple text-sm text-ink-secondary italic">
            {t('stance.quote')}
          </blockquote>
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-5 h-5 text-accent-amber" />
            <h2 className="font-display font-semibold">{t('limitations.title')}</h2>
          </div>
          <ul className="text-sm text-ink-secondary space-y-2 leading-relaxed">
            {limitations.map((item, index) => (
              <li key={index}>· {item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <RefreshCw className="w-5 h-5 text-accent-purple" />
          <h2 className="font-display font-semibold">{t('frequency.title')}</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {frequencyKeys.map((key, index) => (
            <div key={key} className="p-4 rounded-lg bg-bg-surface border border-white/5 text-center">
              <h3 className={`${frequencyColors[index]} font-semibold mb-2`}>
                {t(`frequency.${key}.title`)}
              </h3>
              <p className="text-xs text-ink-secondary">{t(`frequency.${key}.desc`)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
