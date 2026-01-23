import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      // Alldata API
      '/api/v1/datasets': {
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
      // Cube Studio API (OpenAI compatible)
      '/v1/chat': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/v1/models': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/v1/embeddings': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api/v1/models': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Bisheng API
      '/api/v1/workflows': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/rag': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/text2sql': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/chat': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/templates': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'query-vendor': ['@tanstack/react-query'],
        },
      },
    },
  },
});
