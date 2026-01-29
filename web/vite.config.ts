import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      // 启用 Fast Refresh
      fastRefresh: true,
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // 依赖优化配置
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'antd',
      '@ant-design/icons',
      '@tanstack/react-query',
      'zustand',
      'axios',
    ],
    // 排除不需要预构建的依赖
    exclude: ['@vite/client'],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      // Data API
      '/api/v1/datasets': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api/v1/datasources': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api/v1/metadata': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api/v1/query': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // OpenAI Proxy (OpenAI compatible API)
      '/v1/chat': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/v1/models': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/v1/embeddings': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/v1/completions': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      // Admin API (user/group/role/audit/stats management)
      '/api/v1/stats': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/users': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/roles': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/permissions': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/groups': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/admin': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/audit': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/cost': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/settings': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      // Model API (model management)
      '/api/v1/models': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Agent API - all other /api/v1/* routes
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    // 生产环境禁用 sourcemap 以减小包体积
    sourcemap: false,
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 构建目标
    target: 'es2020',
    // 压缩配置 - 使用 esbuild
    minify: 'esbuild',
    // 启用 CSS 压缩
    cssMinify: true,
    // 禁用 gzip 大小报告以加速构建
    reportCompressedSize: false,
    // chunk 大小警告阈值（KB）
    chunkSizeWarningLimit: 500,
    // 资源内联阈值（4KB 以下的资源内联为 base64）
    assetsInlineLimit: 4096,
    rollupOptions: {
      output: {
        // 智能分包策略
        manualChunks: {
          // 将 React 生态系统放在一起，避免循环依赖
          'react-vendor': [
            'react',
            'react-dom',
            'react-router-dom',
            'scheduler',
          ],
          // Ant Design 全家桶（包含所有 rc-* 组件）
          'antd-vendor': ['antd'],
          // 图标单独分包（体积较大）
          'antd-icons': ['@ant-design/icons'],
          // 状态管理
          'state-vendor': ['@tanstack/react-query', 'zustand'],
          // 流程图
          'reactflow-vendor': ['reactflow'],
          // 工具库
          'utils-vendor': ['axios', 'dayjs', 'i18next'],
        },
        // 资源文件名 - 使用内容哈希
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const name = assetInfo.name || '';
          // 图片文件
          if (/\.(png|jpe?g|gif|svg|webp|avif|ico)$/i.test(name)) {
            return 'assets/images/[name]-[hash][extname]';
          }
          // 字体文件
          if (/\.(woff2?|eot|ttf|otf)$/i.test(name)) {
            return 'assets/fonts/[name]-[hash][extname]';
          }
          // CSS 文件
          if (/\.css$/i.test(name)) {
            return 'assets/css/[name]-[hash][extname]';
          }
          // 其他资源
          return 'assets/[name]-[hash][extname]';
        },
      },
      // Tree-shaking 配置
      treeshake: {
        // 标记无副作用的模块
        moduleSideEffects: 'no-external',
        // 保守的属性访问分析
        propertyReadSideEffects: false,
      },
    },
  },
  // 预览服务器配置
  preview: {
    port: 4173,
    host: true,
  },
  // 定义全局常量
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.3.0'),
  },
});
