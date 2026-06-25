# 📱 泡沫雷达 — 移动端打包与更新指南

> 本指南教你如何把「泡沫雷达」网站变成 **手机APP** 和 **电脑应用**，以及**后续如何方便地更新**。

---

## 🎯 一句话总结：推荐用 PWA

**PWA 是更新最方便的选择** —— 你只需部署代码，用户自动收到更新提示，点一下刷新就完成。不需要重新打包、不需要重新安装、不需要上架审核。

APK 适合特定场景（需要上架应用商店、需要原生推送等），但**每次更新都要重新打包 + 用户重新安装**。

---

## ✅ 方案一：PWA（推荐主力方案）

### 更新机制（已自动配置）

我们做了这些优化，让更新体验像原生APP一样丝滑：

| 功能 | 说明 |
|------|------|
| **自动版本检测** | 每次构建时自动更新 Service Worker 版本号，浏览器能立即检测新版本 |
| **弹窗提示更新** | 检测到新版本时，底部弹出「发现新版本，刷新即可更新」提示 |
| **网络优先策略** | 页面（HTML）始终从网络获取最新版本，静态资源缓存加速 |
| **切回检测** | 用户从后台切回前台时，自动检查是否有新版本 |

### 你的更新流程（只需 1 步）

```bash
# 部署代码到服务器（或 Vercel/Netlify/Cloudflare 等）
npm run build
# 然后上传 dist 目录到服务器即可
```

**用户端**：打开应用 → 自动检测到新版本 → 点击「立即更新」→ 页面刷新 → 完成 ✅

就是这么简单，不需要做任何额外工作。

### 📱 手机安装（安卓 / iOS）

1. 用 Chrome / Safari 打开你的网站地址
2. 浏览器底部会弹出 **「添加到主屏幕」** 提示
3. 点击 → 确认 → 桌面出现图标
4. 打开后**全屏运行**，像原生APP一样

> 如果没看到弹窗，点击浏览器菜单（右上角 ⋮ 或底部分享按钮）→ **「添加到主屏幕」**

### 💻 电脑安装（Chrome / Edge）

1. 打开网站
2. 地址栏右侧点击 **⊕ 安装图标**（或菜单 → 应用 → 安装此网站）
3. 安装后从开始菜单 / 桌面启动

### PWA 优势
- ✅ **更新最方便** —— 部署即更新，用户零操作
- ✅ 不需要打包、不需要上架
- ✅ 离线可用（已配置缓存）
- ✅ 不占用手机存储空间

---

## 🚀 方案二：Android APK（备用方案）

> ⚠️ 注意：APK 每次更新都需要重新打包，用户需要重新下载安装。建议仅在需要上架应用商店时使用。

### 环境准备

1. **Node.js**（已有，本项目在用）
2. **Java JDK 17+**（Android 编译需要）
   - 下载：https://www.oracle.com/java/technologies/downloads/#jdk17-windows
   - 或安装 OpenJDK：`choco install openjdk17`
3. **Android Studio**（包含 Android SDK）
   - 下载：https://developer.android.com/studio
   - 安装后打开 Android Studio → SDK Manager → 安装 **Android SDK 34**
   - 记下 SDK 路径（通常是 `C:\Users\<用户名>\AppData\Local\Android\Sdk`）

4. **配置环境变量**（Windows 搜索"环境变量"）
   - `JAVA_HOME` → `C:\Program Files\Java\jdk-17`
   - `ANDROID_HOME` → `C:\Users\<用户名>\AppData\Local\Android\Sdk`
   - PATH 中添加：`%ANDROID_HOME%\platform-tools`

### 打包步骤

#### 第 1 步：安装依赖（在 frontend 目录下执行）

```bash
cd frontend

# 安装 Capacitor 相关包（package.json 已添加，执行 npm install 即可）
npm install

# 同步安装 Android 平台
npx cap add android
```

#### 第 2 步：构建前端 + 同步到 Android 项目

```bash
# 1. 构建生产版本（生成 dist 目录）
npm run build

# 2. 将构建产物同步到 Android 项目
npx cap sync android
```

#### 第 3 步：生成 APK（两种方式）

**方式 A：Android Studio 图形界面（推荐）**

```bash
# 打开 Android Studio 项目
npx cap open android
```

在 Android Studio 中：
1. 等待 Gradle 同步完成（底部进度条）
2. 菜单栏：**Build → Build Bundle(s) / APK(s) → Build APK(s)**
3. 完成后右下角提示，点击 **locate** 找到 APK 文件

APK 路径：`frontend\android\app\build\outputs\apk\debug\app-debug.apk`

**方式 B：命令行（无需打开 Android Studio）**

```bash
cd android

# 构建 Debug APK（测试用）
.\gradlew assembleDebug

# 构建 Release APK（正式用，需要签名）
.\gradlew assembleRelease
```

APK 输出路径：
- Debug：`android\app\build\outputs\apk\debug\app-debug.apk`
- Release：`android\app\build\outputs\apk\release\app-release-unsigned.apk`

#### 第 4 步：签名 Release APK（上架需要）

生成签名密钥（只需一次）：

```bash
cd android

keytool -genkey -v -keystore my-release-key.keystore -alias bubbleradar -keyalg RSA -keysize 2048 -validity 10000
```

在 `android/app/build.gradle` 中添加签名配置：

```gradle
android {
    ...
    signingConfigs {
        release {
            storeFile file("my-release-key.keystore")
            storePassword "你的密码"
            keyAlias "bubbleradar"
            keyPassword "你的密码"
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            ...
        }
    }
}
```

然后重新构建 Release APK。

### APK 更新流程（代码改了重新打包）

```bash
cd frontend

# 1. 重新构建前端
npm run build

# 2. 同步到 Android
npx cap sync android

# 3. 打开 Android Studio 重新构建
npx cap open android
# 或命令行：cd android && .\gradlew assembleDebug
```

**用户端**：需要重新下载 APK → 覆盖安装 → 完成

---

## 📊 方案对比（更新便利性为核心）

| 对比项 | PWA ⭐ | APK |
|--------|--------|-----|
| **更新你的工作量** | 只需 `npm run build` 部署 | 构建 + 打包 + 签名 + 分发 |
| **用户更新操作** | 点击「刷新更新」即可 | 重新下载安装包 → 覆盖安装 |
| **是否需要审核** | 不需要 | 应用商店上架需要审核 |
| **是否需要安装** | 不需要（浏览器安装） | 需要下载 APK |
| **离线可用** | ✅ | ✅ |
| **推送通知** | 有限支持 | 完整支持 |
| **存储占用** | 极小 | 较大（含 WebView） |
| **上架商店** | 不可（但可用浏览器安装） | ✅ 可上架 |

---

## 📁 已添加/修改的文件

| 文件 | 说明 |
|------|------|
| `frontend/capacitor.config.ts` | Capacitor 安卓配置（APK 方案） |
| `frontend/package.json` | 已添加 `@capacitor/*` 依赖；`build` 脚本已集成 SW 版本更新 |
| `frontend/scripts/update-sw-version.mjs` | 构建时自动更新 Service Worker 版本号 |
| `frontend/public/sw.js` | 改进版 Service Worker，支持网络优先 + 更新提示 |
| `frontend/public/manifest.json` | PWA 配置（已有） |
| `frontend/src/components/shared/PwaUpdatePrompt.tsx` | 新版本检测弹窗组件 |
| `frontend/src/App.tsx` | 已集成 PwaUpdatePrompt |

---

## 🎯 最终建议

| 场景 | 推荐方案 |
|------|----------|
| **日常运营，快速迭代** | PWA（主力） |
| **用户自己安装到手机** | PWA（浏览器安装） |
| **需要上架应用商店** | APK（辅助） |
| **需要完整推送通知** | APK（辅助） |
| **两者都要** | 先用 PWA，需要 APK 时再打包 |

**最佳实践**：
1. 先用 PWA 让用户体验（零成本，更新最方便）
2. 需要 APK 时再按上面步骤打包
3. 两者可以共存，代码更新后 PWA 自动生效，APK 需要重新打包

---

如有问题，随时问我！
