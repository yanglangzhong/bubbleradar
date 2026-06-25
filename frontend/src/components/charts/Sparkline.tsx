interface SparklineProps {
  data: number[]
  color?: string
  height?: number
  className?: string
}

export default function Sparkline({ data, color = '#7B61FF', height = 32, className }: SparklineProps) {
  if (data.length < 2) return <div className={className} style={{ height }} />

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const width = 100
  const padding = 2

  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - padding - ((value - min) / range) * (height - padding * 2)
    return `${x},${y}`
  })

  const areaPoints = `${points[0]} ${points.join(' ')} ${width},${height} 0,${height}`

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={className} style={{ height }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={`spark-gradient-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={areaPoints}
        fill={`url(#spark-gradient-${color.replace('#', '')})`}
      />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
