import ReactECharts from 'echarts-for-react'

interface RadarChartProps {
  data: number[]
  labels?: string[]
  height?: number
}

export default function RadarChart({ data, labels = ['房地产', '地方债', '银行系统', '外汇资本', '实体就业', '资本市场'], height = 320 }: RadarChartProps) {
  const option = {
    radar: {
      center: ['50%', '55%'],
      radius: '65%',
      indicator: labels.map((name) => ({ name, max: 100 })),
      axisName: { fontSize: 11, color: '#8a95b0', fontFamily: 'Noto Sans SC' },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: data,
            name: '当前读数',
            areaStyle: { color: 'rgba(196,30,58,0.2)' },
            lineStyle: { color: '#FF2D55', width: 2 },
            itemStyle: { color: '#FF2D55' },
          },
          {
            value: [30, 30, 30, 30, 30, 30],
            name: '安全线',
            areaStyle: { color: 'rgba(0,212,170,0.08)' },
            lineStyle: { color: '#00D4AA', width: 1, type: 'dashed' },
            itemStyle: { color: '#00D4AA' },
          },
        ],
      },
    ],
    legend: {
      bottom: 0,
      textStyle: { fontSize: 10, color: '#8a95b0' },
      data: ['当前读数', '安全线'],
    },
  }

  return <ReactECharts option={option} style={{ height }} className="w-full" />
}
