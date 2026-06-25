import ReactECharts from 'echarts-for-react'

interface HeatmapChartProps {
  labels: string[]
  data: number[][]
  height?: number
}

export default function HeatmapChart({ labels, data, height = 320 }: HeatmapChartProps) {
  const flatData = data.flatMap((row, i) => row.map((v, j) => [j, i, v]))

  const option = {
    tooltip: { position: 'top' },
    grid: { left: '18%', bottom: '18%', top: '5%', right: '15%' },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 9, color: '#8a95b0', rotate: 30, fontFamily: 'Noto Sans SC' },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 9, color: '#8a95b0', fontFamily: 'Noto Sans SC' },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'vertical',
      left: 'right',
      bottom: '15%',
      textStyle: { color: '#8a95b0' },
      inRange: { color: ['#00D4AA', '#162240', '#FF2D55'] },
    },
    series: [
      {
        type: 'heatmap',
        data: flatData,
        label: { show: true, fontSize: 9, fontFamily: 'JetBrains Mono', color: '#e8ecf2' },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height }} className="w-full" />
}
