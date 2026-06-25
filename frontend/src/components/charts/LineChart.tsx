import ReactECharts from 'echarts-for-react'

interface Series {
  name: string
  data: number[]
  color: string
  area?: boolean
}

interface ChartEvent {
  date: string
  title: string
  category?: string
}

interface LineChartProps {
  xAxis: string[]
  series: Series[]
  height?: number
  events?: ChartEvent[]
}

const EVENT_COLORS: Record<string, string> = {
  monetary: '#FF2D55',
  crisis: '#FF2D55',
  geopolitics: '#FF9500',
  trade: '#FF9500',
  pandemic: '#7B61FF',
  default: '#00D4AA',
}

export default function LineChart({ xAxis, series, height = 260, events = [] }: LineChartProps) {
  const markLine = events.length
    ? {
        symbol: ['none', 'none'],
        label: {
          show: true,
          formatter: (p: any) => p.name,
          position: 'insideEndTop',
          fontSize: 9,
          color: '#e8ecf2',
          backgroundColor: 'rgba(0,0,0,0.4)',
          padding: [2, 4],
          borderRadius: 4,
        },
        lineStyle: { type: 'dashed', width: 1 },
        data: events.map((e) => ({
          xAxis: e.date,
          name: e.title,
          lineStyle: { color: EVENT_COLORS[e.category || 'default'] },
        })),
      }
    : undefined

  const option = {
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      right: 0,
      textStyle: { color: '#8a95b0', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
    },
    grid: { left: 40, right: 20, top: 44, bottom: 25 },
    xAxis: {
      type: 'category',
      data: xAxis,
      axisLabel: { fontSize: 10, color: '#556080' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, color: '#556080' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
    },
    series: series.map((s, idx) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      lineStyle: { color: s.color, width: 2 },
      itemStyle: { color: s.color },
      showSymbol: false,
      areaStyle: s.area
        ? { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: s.color + '33' }, { offset: 1, color: s.color + '05' }] } }
        : undefined,
      markLine: idx === 0 ? markLine : undefined,
    })),
  }

  return <ReactECharts option={option} style={{ height }} className="w-full" />
}
