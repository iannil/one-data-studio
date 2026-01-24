import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { QueryClientProvider } from '@tanstack/react-query';
import 'antd/dist/reset.css';
import './index.css';
import App from './App';

// 导入 i18n 配置
import i18n from './i18n';

// 导入统一配置的 QueryClient
import queryClient from './services/queryClient';

// Antd locale 映射
const antdLocales: Record<string, typeof zhCN> = {
  'zh-CN': zhCN,
  'en-US': enUS,
};

// 根组件：监听语言变化并更新 Antd locale
function Root() {
  const [locale, setLocale] = useState(antdLocales[i18n.language] || zhCN);

  useEffect(() => {
    const handleLanguageChange = (lng: string) => {
      setLocale(antdLocales[lng] || zhCN);
    };

    i18n.on('languageChanged', handleLanguageChange);

    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={locale}
        theme={{
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
          },
        }}
      >
        <AntdApp>
          <App />
        </AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
