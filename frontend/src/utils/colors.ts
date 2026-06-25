export const statusColor = (status?: string) => {
  switch (status) {
    case 'danger':
      return 'text-accent-red bg-accent-red/10 border-accent-red/20'
    case 'warn':
      return 'text-accent-amber bg-accent-amber/10 border-accent-amber/20'
    case 'watch':
      return 'text-accent-blue bg-accent-blue/10 border-accent-blue/20'
    case 'safe':
      return 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20'
    default:
      return 'text-ink-secondary bg-white/5 border-white/10'
  }
}

export const statusDot = (status?: string) => {
  switch (status) {
    case 'danger':
      return 'bg-accent-red'
    case 'warn':
      return 'bg-accent-amber'
    case 'watch':
      return 'bg-accent-blue'
    case 'safe':
      return 'bg-accent-cyan'
    default:
      return 'bg-ink-muted'
  }
}

export const scoreStatus = (score: number) => {
  if (score >= 80) return 'danger'
  if (score >= 60) return 'warn'
  if (score >= 40) return 'watch'
  return 'safe'
}

export const scoreText = (score: number) => {
  if (score >= 80) return '危险'
  if (score >= 60) return '预警'
  if (score >= 40) return '关注'
  return '安全'
}
