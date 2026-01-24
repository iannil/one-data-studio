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

// Cube Studio Pages
const NotebooksPage = lazy(() => import('./pages/cube/notebook/NotebooksPage'));
const ExperimentsPage = lazy(() => import('./pages/cube/experiments/ExperimentsPage'));
const ModelsPage = lazy(() => import('./pages/cube/models/ModelsPage'));
const TrainingPage = lazy(() => import('./pages/cube/training/TrainingPage'));
const ServingPage = lazy(() => import('./pages/cube/serving/ServingPage'));
const ResourcesPage = lazy(() => import('./pages/cube/resources/ResourcesPage'));
const MonitoringPage = lazy(() => import('./pages/cube/monitoring/MonitoringPage'));
const AIHubPage = lazy(() => import('./pages/cube/aihub/AIHubPage'));
const PipelinesPage = lazy(() => import('./pages/cube/pipelines/PipelinesPage'));
const LLMTuningPage = lazy(() => import('./pages/cube/llmtuning/LLMTuningPage'));
const SqlLabPage = lazy(() => import('./pages/cube/sql-lab/SqlLabPage'));

// Alldata Pages
const DataSourcesPage = lazy(() => import('./pages/alldata/datasources/DataSourcesPage'));
const ETLPage = lazy(() => import('./pages/alldata/etl/ETLPage'));
const QualityPage = lazy(() => import('./pages/alldata/quality/QualityPage'));
const LineagePage = lazy(() => import('./pages/alldata/lineage/LineagePage'));
const FeaturesPage = lazy(() => import('./pages/alldata/features/FeaturesPage'));
const StandardsPage = lazy(() => import('./pages/alldata/standards/StandardsPage'));
const AssetsPage = lazy(() => import('./pages/alldata/assets/AssetsPage'));
const ServicesPage = lazy(() => import('./pages/alldata/services/ServicesPage'));
const BIPage = lazy(() => import('./pages/alldata/bi/BIPage'));
const MonitoringPageAlldata = lazy(() => import('./pages/alldata/monitoring/MonitoringPage'));
const StreamingPage = lazy(() => import('./pages/alldata/streaming/StreamingPage'));
const StreamingIDEPage = lazy(() => import('./pages/alldata/streaming-ide/StreamingIDEPage'));
const OfflinePage = lazy(() => import('./pages/alldata/offline/OfflinePage'));
const MetricsPage = lazy(() => import('./pages/alldata/metrics/MetricsPage'));

// Bisheng Pages
const PromptsPage = lazy(() => import('./pages/bisheng/prompts/PromptsPage'));
const KnowledgePage = lazy(() => import('./pages/bisheng/knowledge/KnowledgePage'));
const AppsPage = lazy(() => import('./pages/bisheng/apps/AppsPage'));
const EvaluationPage = lazy(() => import('./pages/bisheng/evaluation/EvaluationPage'));
const SFTPage = lazy(() => import('./pages/bisheng/sft/SFTPage'));

// Admin Pages
const UsersPage = lazy(() => import('./pages/admin/users/UsersPage'));
const GroupsPage = lazy(() => import('./pages/admin/groups/GroupsPage'));
const SettingsPage = lazy(() => import('./pages/admin/settings/SettingsPage'));
const AuditPage = lazy(() => import('./pages/admin/audit/AuditPage'));

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

        {/* Cube Studio Routes */}
        <Route path="cube/notebooks" element={<LazyWrapper><NotebooksPage /></LazyWrapper>} />
        <Route path="cube/experiments" element={<LazyWrapper><ExperimentsPage /></LazyWrapper>} />
        <Route path="cube/experiments/compare" element={<LazyWrapper><ExperimentsPage /></LazyWrapper>} />
        <Route path="cube/models" element={<LazyWrapper><ModelsPage /></LazyWrapper>} />
        <Route path="cube/training" element={<LazyWrapper><TrainingPage /></LazyWrapper>} />
        <Route path="cube/serving" element={<LazyWrapper><ServingPage /></LazyWrapper>} />
        <Route path="cube/resources" element={<LazyWrapper><ResourcesPage /></LazyWrapper>} />
        <Route path="cube/monitoring" element={<LazyWrapper><MonitoringPage /></LazyWrapper>} />
        <Route path="cube/aihub" element={<LazyWrapper><AIHubPage /></LazyWrapper>} />
        <Route path="cube/pipelines" element={<LazyWrapper><PipelinesPage /></LazyWrapper>} />
        <Route path="cube/llm-tuning" element={<LazyWrapper><LLMTuningPage /></LazyWrapper>} />
        <Route path="cube/sql-lab" element={<LazyWrapper><SqlLabPage /></LazyWrapper>} />

        {/* Alldata Routes */}
        <Route path="alldata/datasources" element={<LazyWrapper><DataSourcesPage /></LazyWrapper>} />
        <Route path="alldata/etl" element={<LazyWrapper><ETLPage /></LazyWrapper>} />
        <Route path="alldata/quality" element={<LazyWrapper><QualityPage /></LazyWrapper>} />
        <Route path="alldata/lineage" element={<LazyWrapper><LineagePage /></LazyWrapper>} />
        <Route path="alldata/features" element={<LazyWrapper><FeaturesPage /></LazyWrapper>} />
        <Route path="alldata/standards" element={<LazyWrapper><StandardsPage /></LazyWrapper>} />
        <Route path="alldata/assets" element={<LazyWrapper><AssetsPage /></LazyWrapper>} />
        <Route path="alldata/services" element={<LazyWrapper><ServicesPage /></LazyWrapper>} />
        <Route path="alldata/bi" element={<LazyWrapper><BIPage /></LazyWrapper>} />
        <Route path="alldata/monitoring" element={<LazyWrapper><MonitoringPageAlldata /></LazyWrapper>} />
        <Route path="alldata/streaming" element={<LazyWrapper><StreamingPage /></LazyWrapper>} />
        <Route path="alldata/streaming-ide" element={<LazyWrapper><StreamingIDEPage /></LazyWrapper>} />
        <Route path="alldata/offline" element={<LazyWrapper><OfflinePage /></LazyWrapper>} />
        <Route path="alldata/metrics" element={<LazyWrapper><MetricsPage /></LazyWrapper>} />

        {/* Bisheng Routes */}
        <Route path="bisheng/prompts" element={<LazyWrapper><PromptsPage /></LazyWrapper>} />
        <Route path="bisheng/knowledge" element={<LazyWrapper><KnowledgePage /></LazyWrapper>} />
        <Route path="bisheng/apps" element={<LazyWrapper><AppsPage /></LazyWrapper>} />
        <Route path="bisheng/evaluation" element={<LazyWrapper><EvaluationPage /></LazyWrapper>} />
        <Route path="bisheng/sft" element={<LazyWrapper><SFTPage /></LazyWrapper>} />

        {/* Admin Routes */}
        <Route path="admin/users" element={<LazyWrapper><UsersPage /></LazyWrapper>} />
        <Route path="admin/groups" element={<LazyWrapper><GroupsPage /></LazyWrapper>} />
        <Route path="admin/settings" element={<LazyWrapper><SettingsPage /></LazyWrapper>} />
        <Route path="admin/audit" element={<LazyWrapper><AuditPage /></LazyWrapper>} />

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
