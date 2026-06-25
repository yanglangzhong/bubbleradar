import { readFileSync, writeFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

/**
 * 自动更新 Service Worker 缓存版本号
 * 每次构建时生成新的时间戳版本，确保浏览器能检测更新
 */
function updateSwVersion() {
  const swPath = join(__dirname, '..', 'public', 'sw.js')
  const version = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19)

  let content = readFileSync(swPath, 'utf-8')

  // 替换 CACHE_NAME 中的版本号
  content = content.replace(
    /const CACHE_NAME = 'bubbleradar-v[^']*'/,
    `const CACHE_NAME = 'bubbleradar-${version}'`
  )

  writeFileSync(swPath, content, 'utf-8')
  console.log(`✅ Service Worker 版本已更新: bubbleradar-${version}`)
}

updateSwVersion()
