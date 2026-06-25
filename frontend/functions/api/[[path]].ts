/**
 * Cloudflare Pages Function：将所有 /api/* 请求代理到后端服务。
 * 需要在 Cloudflare Pages 环境变量中设置 BACKEND_URL，例如：
 * BACKEND_URL=https://bubbleradar-backend.onrender.com
 */
export const onRequest = async (context: {
  request: Request
  params: { path?: string[] }
  env: { BACKEND_URL?: string }
}): Promise<Response> => {
  const { request, params, env } = context
  const backendUrl = env.BACKEND_URL?.replace(/\/$/, '')

  if (!backendUrl) {
    return new Response(
      JSON.stringify({ error: 'BACKEND_URL not configured' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }

  const pathParts = params.path || []
  const subPath = pathParts.join('/')
  const url = new URL(request.url)
  const targetUrl = `${backendUrl}/api/${subPath}${url.search}`

  const modified = new Request(targetUrl, request)
  return fetch(modified)
}
