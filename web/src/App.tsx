import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import { AuthProvider, ProtectedRoute } from './contexts/AuthContext';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/LoginPage';
import CallbackPage from './pages/CallbackPage';
import DatasetsPage from './pages/datasets/DatasetsPage';
import ChatPage from './pages/chat/ChatPage';
import WorkflowsPage from './pages/workflows/WorkflowsPage';
import WorkflowExecutePage from './pages/workflows/WorkflowExecutePage';
import WorkflowEditorPage from './pages/workflows/WorkflowEditorPage';
import MetadataPage from './pages/metadata/MetadataPage';
import HomePage from './pages/HomePage';

function AppRoutes() {
  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/callback" element={<CallbackPage />} />

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
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="datasets/:id" element={<DatasetsPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="workflows/new" element={<WorkflowEditorPage />} />
        <Route path="workflows/:workflowId/edit" element={<WorkflowEditorPage />} />
        <Route path="workflows/:workflowId/executions" element={<WorkflowExecutePage />} />
        <Route path="metadata" element={<MetadataPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
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
  );
}

export default App;
