import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, X } from 'lucide-react'

/**
 * PWA 更新提示组件
 * 当 Service Worker 检测到新版本时，弹出提示引导用户刷新
 */
export default function PwaUpdatePrompt() {
  const [visible, setVisible] = useState(false)
  const [waitingSW, setWaitingSW] = useState<ServiceWorker | null>(null)

  const handleUpdate = useCallback(() => {
    if (waitingSW) {
      // 发送消息给 SW，让它跳过等待并激活新版本
      waitingSW.postMessage({ type: 'SKIP_WAITING' })
    }
    // 刷新页面加载新版本
    window.location.reload()
  }, [waitingSW])

  const handleDismiss = () => {
    setVisible(false)
  }

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    let isFirstInstall = true

    const handleUpdateFound = (registration: ServiceWorkerRegistration) => {
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        if (!newWorker) return

        newWorker.addEventListener('statechange', () => {
          // 状态变为 installed 且已有旧版本在控制页面 → 说明有新版本等待激活
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // 不是首次安装，而是更新
            if (!isFirstInstall) {
              setWaitingSW(newWorker)
              setVisible(true)
            }
          }
          // 首次安装完成后标记
          if (newWorker.state === 'activated') {
            isFirstInstall = false
          }
        })
      })
    }

    // 注册完成后监听更新
    navigator.serviceWorker.ready.then(handleUpdateFound)

    // 也监听页面可见时的更新（用户切回页面时检查）
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        navigator.serviceWorker.ready.then((reg) => reg.update())
      }
    }
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [])

  if (!visible) return null

  return (
    <div className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 animate-in fade-in slide-in-from-bottom-4 duration-300 sm:left-auto sm:right-4 sm:translate-x-0">
      <div className="flex items-center gap-3 rounded-xl border border-slate-700/60 bg-slate-800/95 px-4 py-3 shadow-2xl backdrop-blur-md">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin text-sky-400" />
          <span className="text-sm text-slate-200">发现新版本，刷新即可更新</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleUpdate}
            className="rounded-lg bg-sky-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-sky-400 active:bg-sky-600"
          >
            立即更新
          </button>
          <button
            onClick={handleDismiss}
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-slate-200"
            aria-label="忽略"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
