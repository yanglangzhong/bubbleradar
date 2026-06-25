import ReactECharts from 'echarts-for-react'

interface GaugeChartProps {
  value: number
  name: string
  color: string
  height?: number
}

export default function GaugeChart({ value, name, color, height = 200 }: GaugeChartProps) {
  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        center: ['50%', '55%'],
        radius: '85%',
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 14,
            color: [
              [0.3, '#00D4AA'],
              [0.6, '#FF9500'],
              [0.8, '#FF2D55'],
              [1, '#C41E3A'],
            ],
          },
        },
        pointer: {
          length: '60%',
          width: 5,
          itemStyle: { color },
        },
        axisTick: { distance: -14, length: 5, lineStyle: { color: '#556080' } },
        splitLine: { distance: -18, length: 10, lineStyle: { color: '#556080' } },
        axisLabel: { distance: 24, fontSize: 9, color: '#8a95b0', fontFamily: 'JetBrains Mono' },
        detail: {
          offsetCenter: [0, '70%'],
          fontSize: 22,
          fontWeight: 'bold',
          fontFamily: 'JetBrains Mono',
          color,
          formatter: '{value}',
        },
        data: [{ value, name }],
      },
    ],
  }

  return <ReactECharts option={option} style={{ height }} className="w-full" />
}
