import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme, Spin } from 'antd';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider, ProtectedRoute } from './contexts/AuthContext';
import { queryClient } from './services/queryClient';
import AppLayout from './components/layout/AppLayout';
import HomePage from './pages/HomePage';

// Sprint 8: 组件懒加载 - 路由级代码分割
const LoginPage = lazy(() => import('./pages/LoginPage'));
const CallbackPage = lazy(() => import('./pages/CallbackPage'));
const DatasetsPage = lazy(() => import('./pages/datasets/DatasetsPage'));
const DocumentsPage = lazy(() => import('./pages/documents/DocumentsPage'));
const ChatPage = lazy(() => import('./pages/chat/ChatPage'));
const WorkflowsPage = lazy(() => import('./pages/workflows/WorkflowsPage'));
const WorkflowExecutePage = lazy(() => import('./pages/workflows/WorkflowExecutePage'));
const WorkflowEditorPage = lazy(() => import('./pages/workflows/WorkflowEditorPage'));
const MetadataPage = lazy(() => import('./pages/metadata/MetadataPage'));
const SchedulesPage = lazy(() => import('./pages/schedules/SchedulesPage'));
const AgentsPage = lazy(() => import('./pages/agents/AgentsPage'));
const Text2SQLPage = lazy(() => import('./pages/text2sql/Text2SQLPage'));
const ExecutionsDashboard = lazy(() => import('./pages/executions/ExecutionsDashboard'));

// 懒加载组件的包装器，显示加载状态
function LazyWrapper({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="Loading..." />
      </div>
    }>
      {children}
    </Suspense>
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<LazyWrapper><LoginPage /></LazyWrapper>} />
      <Route path="/callback" element={<LazyWrapper><CallbackPage /></LazyWrapper>} />

      {/* 受保护路由 */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="datasets" element={<LazyWrapper><DatasetsPage /></LazyWrapper>} />
        <Route path="datasets/:id" element={<LazyWrapper><DatasetsPage /></LazyWrapper>} />
        <Route path="documents" element={<LazyWrapper><DocumentsPage /></LazyWrapper>} />
        <Route path="chat" element={<LazyWrapper><ChatPage /></LazyWrapper>} />
        <Route path="workflows" element={<LazyWrapper><WorkflowsPage /></LazyWrapper>} />
        <Route path="workflows/new" element={<LazyWrapper><WorkflowEditorPage /></LazyWrapper>} />
        <Route path="workflows/:workflowId/edit" element={<LazyWrapper><WorkflowEditorPage /></LazyWrapper>} />
        <Route path="workflows/:workflowId/executions" element={<LazyWrapper><WorkflowExecutePage /></LazyWrapper>} />
        <Route path="metadata" element={<LazyWrapper><MetadataPage /></LazyWrapper>} />
        <Route path="schedules" element={<LazyWrapper><SchedulesPage /></LazyWrapper>} />
        <Route path="agents" element={<LazyWrapper><AgentsPage /></LazyWrapper>} />
        <Route path="text2sql" element={<LazyWrapper><Text2SQLPage /></LazyWrapper>} />
        <Route path="executions" element={<LazyWrapper><ExecutionsDashboard /></LazyWrapper>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1677ff',
            colorBgContainer: '#ffffff',
            colorBgLayout: '#f5f5f5',
            colorBorder: '#e8e8e8',
            colorBorderSecondary: '#f0f0f0',
            borderRadius: 8,
          },
          components: {
            Layout: {
              headerBg: '#ffffff',
              headerHeight: 64,
              siderBg: '#001529',
            },
            Menu: {
              darkItemBg: '#001529',
              darkItemSelectedBg: '#1677ff',
              darkItemHoverBg: '#1677ff',
            },
          },
        }}
      >
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </ConfigProvider>
      {/* 开发环境显示 React Query Devtools */}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} position="bottom" />}
    </QueryClientProvider>
  );
}

export default App;
