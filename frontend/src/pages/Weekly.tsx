import { Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function Weekly() {
  const { t } = useTranslation(['weekly', 'common'])

  const signals = t('signals', { returnObjects: true }) as string[]
  const focus = t('focus', { returnObjects: true }) as string[]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Mail className="w-6 h-6 text-accent-cyan" />
        <h1 className="text-2xl font-display font-bold">{t('title')}</h1>
      </div>

      <div className="card max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-display font-bold">
              {t('issue', { issue: 26, date: t('issueDate') })}
            </h2>
            <p className="text-sm text-ink-secondary mt-1">
              {t('scoreSummary', { score: 68, change: '+3' })}
            </p>
          </div>
          <span className="px-3 py-1 rounded-full bg-accent-amber/10 text-accent-amber border border-accent-amber/20 text-sm font-semibold">
            {t('status.warning')}
          </span>
        </div>

        <div className="space-y-6 text-sm text-ink-secondary leading-relaxed">
          <section>
            <h3 className="text-accent-cyan font-semibold mb-2">{t('sections.keyMetrics')}</h3>
            <p>
              · {t('metrics.aiBubble', { score: 78, zone: t('status.warning'), desc: t('metrics.aiBubbleDesc') })}
            </p>
            <p>
              · {t('metrics.chinaRisk', { score: 62, zone: t('status.watch'), desc: t('metrics.chinaRiskDesc') })}
            </p>
          </section>

          <section>
            <h3 className="text-accent-amber font-semibold mb-2">{t('sections.topSignals')}</h3>
            {signals.map((signal, index) => (
              <p key={index} className={index === 0 ? 'text-accent-red' : 'text-accent-amber'}>
                {index + 1}. {signal}
              </p>
            ))}
          </section>

          <section>
            <h3 className="text-accent-purple font-semibold mb-2">{t('sections.nextFocus')}</h3>
            {focus.map((item, index) => (
              <p key={index}>· {item}</p>
            ))}
          </section>
        </div>

        <div className="mt-8 p-4 rounded-lg bg-accent-cyan/5 border border-accent-cyan/15">
          <h3 className="text-accent-cyan font-semibold mb-2">{t('subscribe.title')}</h3>
          <p className="text-sm text-ink-secondary">{t('subscribe.desc')}</p>
        </div>
      </div>
    </div>
  )
}
