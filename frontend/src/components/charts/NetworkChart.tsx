import ReactECharts from 'echarts-for-react'

interface NetworkNode {
  id: number
  code: string
  name: string
  category: string
  value: number
}

interface NetworkEdge {
  source: number
  target: number
  value: number
}

interface NetworkChartProps {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  height?: number
}

const CATEGORY_COLORS: Record<string, string> = {
  ai: '#7B61FF',
  china: '#C41E3A',
  global: '#00D4AA',
  crypto: '#F7931A',
  default: '#8a95b0',
}

export default function NetworkChart({ nodes, edges, height = 360 }: NetworkChartProps) {
  const categories = Array.from(new Set(nodes.map((n) => n.category))).map((name) => ({ name }))

  const data = nodes.map((n) => ({
    id: n.id,
    name: n.name,
    category: n.category,
    value: n.value,
    symbolSize: Math.max(14, 14 + n.value / 6),
    itemStyle: { color: CATEGORY_COLORS[n.category] || CATEGORY_COLORS.default },
  }))

  const links = edges.map((e) => ({
    source: e.source,
    target: e.target,
    value: e.value,
    lineStyle: {
      width: Math.max(1, Math.abs(e.value) * 4),
      color: e.value > 0 ? '#00D4AA' : '#FF2D55',
      curveness: 0.1,
    },
  }))

  const option = {
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'edge') {
          return `${params.data.source} → ${params.data.target}<br/>相关系数: ${params.data.value}`
        }
        return `${params.data.name}<br/>当前值: ${params.data.value}`
      },
    },
    legend: {
      data: categories.map((c) => c.name),
      textStyle: { color: '#8a95b0', fontSize: 10 },
      top: 0,
      right: 0,
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data,
        links,
        categories,
        roam: true,
        label: {
          show: true,
          color: '#e8ecf2',
          fontSize: 10,
        },
        force: {
          repulsion: 320,
          edgeLength: [60, 180],
          gravity: 0.1,
        },
        lineStyle: {
          opacity: 0.7,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 },
        },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height }} className="w-full" />
}
