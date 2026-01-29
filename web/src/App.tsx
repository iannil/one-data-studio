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
const MetadataGraphPage = lazy(() => import('./pages/metadata/MetadataGraphPage'));
const SchedulesPage = lazy(() => import('./pages/schedules/SchedulesPage'));
const AgentsPage = lazy(() => import('./pages/agents/AgentsPage'));
const Text2SQLPage = lazy(() => import('./pages/text2sql/Text2SQLPage'));
const ExecutionsDashboard = lazy(() => import('./pages/executions/ExecutionsDashboard'));

// Model Pages
const NotebooksPage = lazy(() => import('./pages/model/notebook/NotebooksPage'));
const ExperimentsPage = lazy(() => import('./pages/model/experiments/ExperimentsPage'));
const ModelsPage = lazy(() => import('./pages/model/models/ModelsPage'));
const TrainingPage = lazy(() => import('./pages/model/training/TrainingPage'));
const ServingPage = lazy(() => import('./pages/model/serving/ServingPage'));
const ResourcesPage = lazy(() => import('./pages/model/resources/ResourcesPage'));
const MonitoringPage = lazy(() => import('./pages/model/monitoring/MonitoringPage'));
const AIHubPage = lazy(() => import('./pages/model/aihub/AIHubPage'));
const PipelinesPage = lazy(() => import('./pages/model/pipelines/PipelinesPage'));
const LLMTuningPage = lazy(() => import('./pages/model/llmtuning/LLMTuningPage'));
const SqlLabPage = lazy(() => import('./pages/model/sql-lab/SqlLabPage'));

// Data Pages
const DataSourcesPage = lazy(() => import('./pages/data/datasources/DataSourcesPage'));
const ETLPage = lazy(() => import('./pages/data/etl/ETLPage'));
const KettlePanel = lazy(() => import('./pages/data/etl/KettlePanel'));
const QualityPage = lazy(() => import('./pages/data/quality/QualityPage'));
const LineagePage = lazy(() => import('./pages/data/lineage/LineagePage'));
const FeaturesPage = lazy(() => import('./pages/data/features/FeaturesPage'));
const StandardsPage = lazy(() => import('./pages/data/standards/StandardsPage'));
const AssetsPage = lazy(() => import('./pages/data/assets/AssetsPage'));
const ServicesPage = lazy(() => import('./pages/data/services/ServicesPage'));
const BIPage = lazy(() => import('./pages/data/bi/BIPage'));
const MonitoringPageData = lazy(() => import('./pages/data/monitoring/MonitoringPage'));
const StreamingPage = lazy(() => import('./pages/data/streaming/StreamingPage'));
const StreamingIDEPage = lazy(() => import('./pages/data/streaming-ide/StreamingIDEPage'));
const OfflinePage = lazy(() => import('./pages/data/offline/OfflinePage'));
const MetricsPage = lazy(() => import('./pages/data/metrics/MetricsPage'));
const AlertsPage = lazy(() => import('./pages/data/monitoring/AlertsPage'));
const OCRPage = lazy(() => import('./pages/data/ocr/OCRPage'));
const KettleGeneratorPage = lazy(() => import('./pages/data/etl/KettlePage'));

// Agent Pages
const PromptsPage = lazy(() => import('./pages/agent-platform/prompts/PromptsPage'));
const KnowledgePage = lazy(() => import('./pages/agent-platform/knowledge/KnowledgePage'));
const AppsPage = lazy(() => import('./pages/agent-platform/apps/AppsPage'));
const EvaluationPage = lazy(() => import('./pages/agent-platform/evaluation/EvaluationPage'));
const SFTPage = lazy(() => import('./pages/agent-platform/sft/SFTPage'));

// Admin Pages
const UsersPage = lazy(() => import('./pages/admin/users/UsersPage'));
const GroupsPage = lazy(() => import('./pages/admin/groups/GroupsPage'));
const SettingsPage = lazy(() => import('./pages/admin/settings/SettingsPage'));
const AuditPage = lazy(() => import('./pages/admin/audit/AuditPage'));
const RolesPage = lazy(() => import('./pages/admin/RolesPage'));
const CostReportPage = lazy(() => import('./pages/admin/CostReportPage'));
const AdminNotificationsPage = lazy(() => import('./pages/admin/NotificationsPage'));
const ContentPage = lazy(() => import('./pages/admin/ContentPage'));
const UserProfilesPage = lazy(() => import('./pages/admin/UserProfilesPage'));
const UserSegmentsPage = lazy(() => import('./pages/admin/UserSegmentsPage'));
const ApiTesterPage = lazy(() => import('./pages/admin/ApiTester'));

// Admin Behavior Pages
const BehaviorDashboardPage = lazy(() => import('./pages/admin/behavior/BehaviorDashboard'));
const AuditLogPage = lazy(() => import('./pages/admin/behavior/AuditLogPage'));
const ProfileViewPage = lazy(() => import('./pages/admin/behavior/ProfileView'));

// Portal Pages
const PortalDashboardPage = lazy(() => import('./pages/portal/DashboardPage'));
const PortalNotificationsPage = lazy(() => import('./pages/portal/NotificationsPage'));
const TodosPage = lazy(() => import('./pages/portal/TodosPage'));
const AnnouncementsPage = lazy(() => import('./pages/portal/AnnouncementsPage'));
const ProfilePage = lazy(() => import('./pages/portal/ProfilePage'));

// Scheduler Pages
const SmartSchedulerPage = lazy(() => import('./pages/scheduler/SmartSchedulerPage'));

// Metadata Pages
const MetadataVersionDiffPage = lazy(() => import('./pages/metadata/VersionDiffPage'));

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
        <Route path="metadata/graph" element={<LazyWrapper><MetadataGraphPage /></LazyWrapper>} />
        <Route path="metadata/version-diff" element={<LazyWrapper><MetadataVersionDiffPage /></LazyWrapper>} />
        <Route path="schedules" element={<LazyWrapper><SchedulesPage /></LazyWrapper>} />
        <Route path="agents" element={<LazyWrapper><AgentsPage /></LazyWrapper>} />
        <Route path="text2sql" element={<LazyWrapper><Text2SQLPage /></LazyWrapper>} />
        <Route path="executions" element={<LazyWrapper><ExecutionsDashboard /></LazyWrapper>} />

        {/* Model Routes */}
        <Route path="model/notebooks" element={<LazyWrapper><NotebooksPage /></LazyWrapper>} />
        <Route path="model/experiments" element={<LazyWrapper><ExperimentsPage /></LazyWrapper>} />
        <Route path="model/experiments/compare" element={<LazyWrapper><ExperimentsPage /></LazyWrapper>} />
        <Route path="model/models" element={<LazyWrapper><ModelsPage /></LazyWrapper>} />
        <Route path="model/training" element={<LazyWrapper><TrainingPage /></LazyWrapper>} />
        <Route path="model/serving" element={<LazyWrapper><ServingPage /></LazyWrapper>} />
        <Route path="model/resources" element={<LazyWrapper><ResourcesPage /></LazyWrapper>} />
        <Route path="model/monitoring" element={<LazyWrapper><MonitoringPage /></LazyWrapper>} />
        <Route path="model/aihub" element={<LazyWrapper><AIHubPage /></LazyWrapper>} />
        <Route path="model/pipelines" element={<LazyWrapper><PipelinesPage /></LazyWrapper>} />
        <Route path="model/llm-tuning" element={<LazyWrapper><LLMTuningPage /></LazyWrapper>} />
        <Route path="model/sql-lab" element={<LazyWrapper><SqlLabPage /></LazyWrapper>} />

        {/* Data Routes */}
        <Route path="data/datasources" element={<LazyWrapper><DataSourcesPage /></LazyWrapper>} />
        <Route path="data/etl" element={<LazyWrapper><ETLPage /></LazyWrapper>} />
        <Route path="data/kettle" element={<LazyWrapper><KettlePanel /></LazyWrapper>} />
        <Route path="data/quality" element={<LazyWrapper><QualityPage /></LazyWrapper>} />
        <Route path="data/lineage" element={<LazyWrapper><LineagePage /></LazyWrapper>} />
        <Route path="data/features" element={<LazyWrapper><FeaturesPage /></LazyWrapper>} />
        <Route path="data/standards" element={<LazyWrapper><StandardsPage /></LazyWrapper>} />
        <Route path="data/assets" element={<LazyWrapper><AssetsPage /></LazyWrapper>} />
        <Route path="data/services" element={<LazyWrapper><ServicesPage /></LazyWrapper>} />
        <Route path="data/bi" element={<LazyWrapper><BIPage /></LazyWrapper>} />
        <Route path="data/monitoring" element={<LazyWrapper><MonitoringPageData /></LazyWrapper>} />
        <Route path="data/streaming" element={<LazyWrapper><StreamingPage /></LazyWrapper>} />
        <Route path="data/streaming-ide" element={<LazyWrapper><StreamingIDEPage /></LazyWrapper>} />
        <Route path="data/offline" element={<LazyWrapper><OfflinePage /></LazyWrapper>} />
        <Route path="data/metrics" element={<LazyWrapper><MetricsPage /></LazyWrapper>} />
        <Route path="data/alerts" element={<LazyWrapper><AlertsPage /></LazyWrapper>} />
        <Route path="data/ocr" element={<LazyWrapper><OCRPage /></LazyWrapper>} />
        <Route path="data/kettle-generator" element={<LazyWrapper><KettleGeneratorPage /></LazyWrapper>} />

        {/* Agent Routes */}
        <Route path="agent-platform/prompts" element={<LazyWrapper><PromptsPage /></LazyWrapper>} />
        <Route path="agent-platform/knowledge" element={<LazyWrapper><KnowledgePage /></LazyWrapper>} />
        <Route path="agent-platform/apps" element={<LazyWrapper><AppsPage /></LazyWrapper>} />
        <Route path="agent-platform/evaluation" element={<LazyWrapper><EvaluationPage /></LazyWrapper>} />
        <Route path="agent-platform/sft" element={<LazyWrapper><SFTPage /></LazyWrapper>} />

        {/* Admin Routes */}
        <Route path="admin/users" element={<LazyWrapper><UsersPage /></LazyWrapper>} />
        <Route path="admin/groups" element={<LazyWrapper><GroupsPage /></LazyWrapper>} />
        <Route path="admin/settings" element={<LazyWrapper><SettingsPage /></LazyWrapper>} />
        <Route path="admin/audit" element={<LazyWrapper><AuditPage /></LazyWrapper>} />
        <Route path="admin/roles" element={<LazyWrapper><RolesPage /></LazyWrapper>} />
        <Route path="admin/cost-report" element={<LazyWrapper><CostReportPage /></LazyWrapper>} />
        <Route path="admin/notifications" element={<LazyWrapper><AdminNotificationsPage /></LazyWrapper>} />
        <Route path="admin/content" element={<LazyWrapper><ContentPage /></LazyWrapper>} />
        <Route path="admin/user-profiles" element={<LazyWrapper><UserProfilesPage /></LazyWrapper>} />
        <Route path="admin/user-segments" element={<LazyWrapper><UserSegmentsPage /></LazyWrapper>} />
        <Route path="admin/api-tester" element={<LazyWrapper><ApiTesterPage /></LazyWrapper>} />
        <Route path="admin/behavior" element={<LazyWrapper><BehaviorDashboardPage /></LazyWrapper>} />
        <Route path="admin/behavior/audit-log" element={<LazyWrapper><AuditLogPage /></LazyWrapper>} />
        <Route path="admin/behavior/profile-view" element={<LazyWrapper><ProfileViewPage /></LazyWrapper>} />

        {/* Portal Routes */}
        <Route path="portal/dashboard" element={<LazyWrapper><PortalDashboardPage /></LazyWrapper>} />
        <Route path="portal/notifications" element={<LazyWrapper><PortalNotificationsPage /></LazyWrapper>} />
        <Route path="portal/todos" element={<LazyWrapper><TodosPage /></LazyWrapper>} />
        <Route path="portal/announcements" element={<LazyWrapper><AnnouncementsPage /></LazyWrapper>} />
        <Route path="portal/profile" element={<LazyWrapper><ProfilePage /></LazyWrapper>} />

        {/* Scheduler Routes */}
        <Route path="scheduler/smart" element={<LazyWrapper><SmartSchedulerPage /></LazyWrapper>} />

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
