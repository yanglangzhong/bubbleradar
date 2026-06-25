import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// Common namespaces
import zhCommon from './locales/zh/common.json'
import enCommon from './locales/en/common.json'
import zhNav from './locales/zh/nav.json'
import enNav from './locales/en/nav.json'
import zhAuth from './locales/zh/auth.json'
import enAuth from './locales/en/auth.json'

// Page namespaces
import zhLogin from './locales/zh/pages/login.json'
import enLogin from './locales/en/pages/login.json'
import zhDashboard from './locales/zh/pages/dashboard.json'
import enDashboard from './locales/en/pages/dashboard.json'
import zhBacktest from './locales/zh/pages/backtest.json'
import enBacktest from './locales/en/pages/backtest.json'
import zhAIBubble from './locales/zh/pages/aiBubble.json'
import enAIBubble from './locales/en/pages/aiBubble.json'
import zhChinaRisk from './locales/zh/pages/chinaRisk.json'
import enChinaRisk from './locales/en/pages/chinaRisk.json'
import zhGlobalContagion from './locales/zh/pages/globalContagion.json'
import enGlobalContagion from './locales/en/pages/globalContagion.json'
import zhCrypto from './locales/zh/pages/crypto.json'
import enCrypto from './locales/en/pages/crypto.json'
import zhDataLab from './locales/zh/pages/dataLab.json'
import enDataLab from './locales/en/pages/dataLab.json'
import zhHeatmap from './locales/zh/pages/heatmap.json'
import enHeatmap from './locales/en/pages/heatmap.json'
import zhWeekly from './locales/zh/pages/weekly.json'
import enWeekly from './locales/en/pages/weekly.json'
import zhAbout from './locales/zh/pages/about.json'
import enAbout from './locales/en/pages/about.json'
import zhCrisisArchive from './locales/zh/pages/crisisArchive.json'
import enCrisisArchive from './locales/en/pages/crisisArchive.json'

const resources = {
  zh: {
    common: zhCommon,
    nav: zhNav,
    auth: zhAuth,
    login: zhLogin,
    dashboard: zhDashboard,
    backtest: zhBacktest,
    aiBubble: zhAIBubble,
    chinaRisk: zhChinaRisk,
    globalContagion: zhGlobalContagion,
    crypto: zhCrypto,
    dataLab: zhDataLab,
    heatmap: zhHeatmap,
    weekly: zhWeekly,
    about: zhAbout,
    crisisArchive: zhCrisisArchive,
  },
  en: {
    common: enCommon,
    nav: enNav,
    auth: enAuth,
    login: enLogin,
    dashboard: enDashboard,
    backtest: enBacktest,
    aiBubble: enAIBubble,
    chinaRisk: enChinaRisk,
    globalContagion: enGlobalContagion,
    crypto: enCrypto,
    dataLab: enDataLab,
    heatmap: enHeatmap,
    weekly: enWeekly,
    about: enAbout,
    crisisArchive: enCrisisArchive,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    defaultNS: 'common',
    fallbackLng: 'zh',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  })

export default i18n
