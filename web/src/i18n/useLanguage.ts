/**
 * useLanguage Hook
 * Sprint 19: 国际化支持
 *
 * 提供语言切换功能的 React Hook
 */

import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { supportedLanguages, changeLanguage } from './index';

export interface LanguageOption {
  code: string;
  name: string;
  flag: string;
}

export interface UseLanguageReturn {
  /** 当前语言代码 */
  currentLanguage: string;
  /** 可用的语言列表 */
  availableLanguages: LanguageOption[];
  /** 切换语言函数 */
  setLanguage: (languageCode: string) => Promise<void>;
  /** 当前语言是否为中文 */
  isChinese: boolean;
  /** 当前语言是否为英文 */
  isEnglish: boolean;
}

/**
 * 语言切换 Hook
 *
 * @example
 * ```tsx
 * const { currentLanguage, availableLanguages, setLanguage } = useLanguage();
 *
 * return (
 *   <Select
 *     value={currentLanguage}
 *     onChange={setLanguage}
 *     options={availableLanguages.map(lang => ({
 *       value: lang.code,
 *       label: `${lang.flag} ${lang.name}`
 *     }))}
 *   />
 * );
 * ```
 */
export function useLanguage(): UseLanguageReturn {
  const { i18n } = useTranslation();

  const setLanguage = useCallback(
    async (languageCode: string) => {
      await changeLanguage(languageCode);
    },
    []
  );

  return {
    currentLanguage: i18n.language,
    availableLanguages: supportedLanguages,
    setLanguage,
    isChinese: i18n.language.startsWith('zh'),
    isEnglish: i18n.language.startsWith('en'),
  };
}

export default useLanguage;
