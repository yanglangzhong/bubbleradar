import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  zh: {
    nav: {
      app: { name: 'BubbleRadar' },
      live: '实时',
      home: '首页',
      aiBubble: 'AI泡沫',
      chinaRisk: '中国风险',
      global: '全球传染',
      archive: '危机档案',
      heatmap: '热力图',
      crypto: '加密风险',
      backtest: '策略回测',
      lab: '数据实验室',
      weekly: '每周警报',
      about: '关于',
    },
    common: {
      loading: '加载中…',
      retry: '重试',
    },
    auth: {
      login: '登录',
      logout: '退出登录',
      defaultAccount: '默认账号：admin@example.com / admin',
    },
    login: {
      title: '登录 BubbleRadar',
      subtitle: '请输入管理员账号继续访问',
      email: '邮箱',
      password: '密码',
      submit: '登录',
      loggingIn: '登录中…',
      error: '登录失败，请检查邮箱和密码',
      defaultAccount: '默认账号：admin@example.com / admin',
    },
  },
  en: {
    nav: {
      app: { name: 'BubbleRadar' },
      live: 'LIVE',
      home: 'Home',
      aiBubble: 'AI Bubble',
      chinaRisk: 'China Risk',
      global: 'Global Contagion',
      archive: 'Crisis Archive',
      heatmap: 'Heatmap',
      crypto: 'Crypto Risk',
      backtest: 'Backtest',
      lab: 'Data Lab',
      weekly: 'Weekly Alert',
      about: 'About',
    },
    common: {
      loading: 'Loading...',
      retry: 'Retry',
    },
    auth: {
      login: 'Login',
      logout: 'Logout',
      defaultAccount: 'Default account: admin@example.com / admin',
    },
    login: {
      title: 'Login to BubbleRadar',
      subtitle: 'Please enter admin credentials to continue',
      email: 'Email',
      password: 'Password',
      submit: 'Login',
      loggingIn: 'Logging in...',
      error: 'Login failed, please check your email and password',
      defaultAccount: 'Default account: admin@example.com / admin',
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: 'zh',
  fallbackLng: 'zh',
  interpolation: { escapeValue: false },
  defaultNS: 'nav',
})

export default i18n