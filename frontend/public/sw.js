const CACHE_NAME = 'bubbleradar-2026-06-25-01-31-37'
const PRECACHE_ASSETS = ['/', '/index.html']

// 监听主线程发来的消息，用于跳过等待
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

// 安装阶段预缓存入口
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  )
})

// 激活时清理旧缓存，并接管所有客户端
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        )
      )
      .then(() => self.clients.claim())
  )
})

// 智能缓存策略：
// - 导航请求（页面）：网络优先，确保用户始终获取最新版本
// - 静态资源（JS/CSS/图片）：缓存优先，提升加载速度
// - API/WebSocket：不缓存
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // 跳过非 GET 请求、浏览器扩展请求和远程 API/WebSocket
  if (
    request.method !== 'GET' ||
    url.protocol === 'chrome-extension:' ||
    url.protocol === 'ws:' ||
    url.protocol === 'wss:' ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/ws')
  ) {
    return
  }

  // 导航请求（HTML页面）：网络优先，确保版本最新
  if (request.mode === 'navigate' || url.pathname === '/' || url.pathname === '/index.html') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const cloned = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, cloned))
          return response
        })
        .catch(() => {
          return caches.match(request).then((cached) => {
            if (cached) return cached
            return caches.match('/index.html')
          })
        })
    )
    return
  }

  // 静态资源：缓存优先，网络失败时用缓存兜底
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached
      }

      return fetch(request)
        .then((response) => {
          const cloned = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, cloned))
          return response
        })
        .catch(() => {
          throw new Error('Network request failed and no cache available')
        })
    })
  )
})
