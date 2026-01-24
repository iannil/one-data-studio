/**
 * i18n 配置
 * Sprint 19: 国际化支持
 *
 * 使用 react-i18next 实现多语言支持
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// 导入翻译文件
import zhCNCommon from './zh-CN/common.json';
import zhCNPages from './zh-CN/pages.json';
import zhCNErrors from './zh-CN/errors.json';

import enUSCommon from './en-US/common.json';
import enUSPages from './en-US/pages.json';
import enUSErrors from './en-US/errors.json';

// 翻译资源
const resources = {
  'zh-CN': {
    common: zhCNCommon,
    pages: zhCNPages,
    errors: zhCNErrors,
  },
  'en-US': {
    common: enUSCommon,
    pages: enUSPages,
    errors: enUSErrors,
  },
};

// 支持的语言列表
export const supportedLanguages = [
  { code: 'zh-CN', name: '简体中文', flag: '🇨🇳' },
  { code: 'en-US', name: 'English', flag: '🇺🇸' },
];

// 默认命名空间
export const defaultNS = 'common';

// 初始化 i18n
i18n
  // 自动检测用户语言
  .use(LanguageDetector)
  // 集成 react-i18next
  .use(initReactI18next)
  // 初始化配置
  .init({
    resources,
    fallbackLng: 'zh-CN', // 默认语言
    defaultNS,

    // 命名空间
    ns: ['common', 'pages', 'errors'],

    // 语言检测选项
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18n_language',
    },

    // 调试模式（开发环境）
    debug: process.env.NODE_ENV === 'development',

    // React 特定选项
    react: {
      useSuspense: true,
    },

    // 插值选项
    interpolation: {
      escapeValue: false, // React 已经处理了 XSS
    },

    // 缺失键处理
    saveMissing: process.env.NODE_ENV === 'development',
    missingKeyHandler: (lngs, ns, key) => {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`Missing translation key: ${ns}:${key}`);
      }
    },
  });

// 切换语言
export const changeLanguage = async (lng: string) => {
  await i18n.changeLanguage(lng);
  // 更新 HTML lang 属性
  document.documentElement.lang = lng;
  // 可以在这里添加其他语言切换逻辑，如更新 Ant Design 的语言包
};

// 获取当前语言
export const getCurrentLanguage = () => i18n.language;

// 检查是否支持某语言
export const isLanguageSupported = (lng: string) =>
  supportedLanguages.some((l) => l.code === lng);

export default i18n;
