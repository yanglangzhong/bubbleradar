export const formatNumber = (n?: number, digits = 2) => {
  if (n === undefined || n === null) return '--'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export const formatDate = (s?: string) => {
  if (!s) return '--'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

export const formatTime = (s?: string) => {
  if (!s) return '--'
  return new Date(s).toLocaleTimeString('zh-CN', { hour12: false })
}
