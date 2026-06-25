import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { withTranslation, type WithTranslation } from 'react-i18next'

interface Props extends WithTranslation {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, info)
  }

  render() {
    const { t, children, fallback } = this.props

    if (this.state.hasError) {
      if (fallback) {
        return fallback
      }

      return (
        <div className="min-h-[60vh] flex flex-col items-center justify-center p-6 text-center animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-accent-red/10 border border-accent-red/20 flex items-center justify-center mb-4">
            <AlertTriangle className="w-8 h-8 text-accent-red" />
          </div>
          <h2 className="text-xl font-display font-bold text-ink-primary mb-2">
            {t('error.pageError')}
          </h2>
          <p className="text-sm text-ink-secondary max-w-md mb-6">
            {t('error.pageErrorDesc')}
          </p>
          {this.state.error && (
            <pre className="text-xs text-ink-muted bg-bg-surface border border-white/5 rounded-lg p-3 max-w-xl overflow-auto mb-6">
              {this.state.error.message}
            </pre>
          )}
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 text-accent-cyan hover:bg-accent-cyan/30 transition-colors text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              {t('error.reload')}
            </button>
            <a
              href="/"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-ink-primary hover:bg-white/10 transition-colors text-sm font-medium"
            >
              {t('error.backHome')}
            </a>
          </div>
        </div>
      )
    }

    return children
  }
}

const TranslatedErrorBoundary = withTranslation('common')(ErrorBoundary)
export default TranslatedErrorBoundary
