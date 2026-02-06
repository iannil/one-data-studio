/**
 * TodosPage 组件测试
 * 测试待办事项页面
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/testUtils';
import userEvent from '@testing-library/user-event';

import type { UserTodo } from '../../services/admin';

// Mock admin service
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../services/admin', () => ({
  getUserTodos: vi.fn(() => Promise.resolve({
    code: 0,
    data: {
      todos: [],
      total: 0,
      pending_count: 0,
      overdue_count: 0,
      page: 1,
      page_size: 20,
    },
  })),
  getTodosSummary: vi.fn(() => Promise.resolve({
    code: 0,
    data: {
      by_status: {
        pending: 5,
        in_progress: 2,
        completed: 10,
        cancelled: 1,
      },
      by_type: {
        approval: 2,
        task: 3,
        reminder: 1,
      },
      overdue_count: 1,
      due_today: 2,
    },
  })),
  startTodo: vi.fn(() => Promise.resolve({
    code: 0,
    data: { id: 'todo-1', status: 'in_progress' },
  })),
  completeTodo: vi.fn(() => Promise.resolve({
    code: 0,
    data: { id: 'todo-1', status: 'completed' },
  })),
  cancelTodo: vi.fn(() => Promise.resolve({ code: 0 })),
}));

import TodosPage from './TodosPage';
import {
  getUserTodos,
  getTodosSummary,
  startTodo,
  completeTodo,
  cancelTodo,
} from '../../services/admin';

// Mock data
const mockTodos: UserTodo[] = [
  {
    id: 'todo-1',
    user_id: 'user-1',
    title: '审核数据集申请',
    description: '请审核新的数据集访问申请，需要检查权限配置',
    todo_type: 'approval',
    priority: 'urgent',
    source_name: 'Data API',
    source_url: '/data/datasets/123',
    status: 'pending',
    is_overdue: false,
    due_date: '2026-02-10T18:00:00Z',
    created_at: '2026-02-06T09:00:00Z',
  },
  {
    id: 'todo-2',
    user_id: 'user-1',
    title: '执行数据质量检查',
    description: '运行每日数据质量检查任务',
    todo_type: 'task',
    priority: 'high',
    source_name: 'Workflow',
    source_url: '/workflows/quality-check',
    status: 'in_progress',
    is_overdue: false,
    due_date: '2026-02-07T12:00:00Z',
    created_at: '2026-02-06T08:00:00Z',
  },
  {
    id: 'todo-3',
    user_id: 'user-1',
    title: '更新模型配置',
    description: '根据最新需求更新模型参数',
    todo_type: 'task',
    priority: 'medium',
    source_name: 'MLOps',
    status: 'pending',
    is_overdue: true,
    due_date: '2026-02-05T18:00:00Z',
    created_at: '2026-02-04T10:00:00Z',
  },
  {
    id: 'todo-4',
    user_id: 'user-1',
    title: '查看月度报告',
    description: '查看上月数据统计报告',
    todo_type: 'reminder',
    priority: 'low',
    source_name: '系统',
    status: 'completed',
    is_overdue: false,
    created_at: '2026-02-01T10:00:00Z',
    completed_at: '2026-02-02T15:00:00Z',
  },
  {
    id: 'todo-5',
    user_id: 'user-1',
    title: '代码评审',
    description: '评审新功能的代码变更',
    todo_type: 'review',
    priority: 'high',
    source_name: 'GitLab',
    source_url: '/projects/1/merge-requests/10',
    status: 'pending',
    is_overdue: false,
    created_at: '2026-02-06T07:00:00Z',
  },
];

const mockTodoResponse = {
  code: 0,
  data: {
    todos: mockTodos,
    total: 5,
    pending_count: 3,
    overdue_count: 1,
    page: 1,
    page_size: 20,
  },
};

const mockSummaryResponse = {
  code: 0,
  data: {
    by_status: {
      pending: 3,
      in_progress: 1,
      completed: 1,
      cancelled: 0,
    },
    by_type: {
      approval: 1,
      task: 2,
      reminder: 1,
      review: 1,
    },
    overdue_count: 1,
    due_today: 2,
  },
};

describe('TodosPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getUserTodos).mockResolvedValue(mockTodoResponse);
    vi.mocked(getTodosSummary).mockResolvedValue(mockSummaryResponse);
  });

  describe('基本渲染', () => {
    it('应该正确渲染页面标题', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('待办事项')).toBeInTheDocument();
      });
    });

    it('应该显示待办统计信息', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText(/共 5 条待办/)).toBeInTheDocument();
        expect(screen.getByText(/1 条已逾期/)).toBeInTheDocument();
      });
    });

    it('应该显示刷新按钮', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('刷新')).toBeInTheDocument();
      });
    });
  });

  describe('统计卡片', () => {
    it('应该显示待处理卡片', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        // 使用 queryAllByText 并检查数量
        const pendingTexts = screen.queryAllByText('待处理');
        expect(pendingTexts.length).toBeGreaterThan(0);
      });
    });

    it('应该显示进行中卡片', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const inProgressTexts = screen.queryAllByText('进行中');
        expect(inProgressTexts.length).toBeGreaterThan(0);
      });
    });

    it('应该显示已逾期卡片', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const overdueTexts = screen.queryAllByText('已逾期');
        expect(overdueTexts.length).toBeGreaterThan(0);
      });
    });

    it('应该显示完成率', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const rateTexts = screen.queryAllByText('20%');
        expect(rateTexts.length).toBeGreaterThan(0);
      });
    });
  });

  describe('标签页', () => {
    it('应该显示所有标签页', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        // 检查标签是否被渲染
        const tabTexts = ['待处理', '进行中', '已完成', '全部'];
        tabTexts.forEach(text => {
          const tabs = screen.queryAllByText(text);
          expect(tabs.length).toBeGreaterThan(0);
        });
      });
    });
  });

  describe('待办列表', () => {
    it('应该渲染待办表格', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('审核数据集申请')).toBeInTheDocument();
        expect(screen.getByText('执行数据质量检查')).toBeInTheDocument();
        expect(screen.getByText('更新模型配置')).toBeInTheDocument();
        expect(screen.getByText('查看月度报告')).toBeInTheDocument();
        expect(screen.getByText('代码评审')).toBeInTheDocument();
      });
    });

    it('应该显示来源信息', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('Data API')).toBeInTheDocument();
        expect(screen.getByText('Workflow')).toBeInTheDocument();
        expect(screen.getByText('MLOps')).toBeInTheDocument();
        expect(screen.getByText('GitLab')).toBeInTheDocument();
      });
    });

    it('应该显示截止时间', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText(/2026-02-10/)).toBeInTheDocument();
        expect(screen.getByText(/2026-02-07/)).toBeInTheDocument();
      });
    });
  });

  describe('交互功能 - 点击待办', () => {
    it('点击有 source_url 的待办应该导航', async () => {
      const user = userEvent.setup();
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('审核数据集申请')).toBeInTheDocument();
      });

      const todoLink = screen.getByText('审核数据集申请');
      await user.click(todoLink);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/data/datasets/123');
      });
    });
  });

  describe('筛选功能', () => {
    it('应该有搜索框', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('搜索待办...');
        expect(searchInput).toBeInTheDocument();
      });
    });

    it('应该有类型筛选下拉框', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        // 查找筛选框的容器
        const filterContainer = document.querySelector('.ant-select');
        expect(filterContainer).toBeInTheDocument();
      });
    });

    it('应该有优先级筛选下拉框', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        // 查找筛选框的容器
        const filterContainers = document.querySelectorAll('.ant-select');
        expect(filterContainers.length).toBeGreaterThan(0);
      });
    });
  });

  describe('分页功能', () => {
    it('应该显示分页器', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const totalElements = screen.queryAllByText(/共 \d+ 条/);
        expect(totalElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('刷新功能', () => {
    it('点击刷新按钮应该重新获取数据', async () => {
      const user = userEvent.setup();
      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('刷新')).toBeInTheDocument();
      });

      const refreshButton = screen.getByText('刷新');
      await user.click(refreshButton);

      await waitFor(() => {
        expect(getUserTodos).toHaveBeenCalled();
      });
    });
  });

  describe('空状态', () => {
    it('无待办时应该显示空状态', async () => {
      vi.mocked(getUserTodos).mockResolvedValueOnce({
        code: 0,
        data: {
         todos: [],
          total: 0,
          pending_count: 0,
          overdue_count: 0,
          page: 1,
          page_size: 20,
        },
      });

      render(<TodosPage />);

      await waitFor(() => {
        expect(screen.getByText('暂无待办')).toBeInTheDocument();
      });
    });
  });

  describe('辅助函数', () => {
    it('应该显示不同优先级标签', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const urgentTags = screen.queryAllByText('紧急');
        const highTags = screen.queryAllByText('高');
        const mediumTags = screen.queryAllByText('中');
        const lowTags = screen.queryAllByText('低');

        expect(urgentTags.length).toBeGreaterThan(0);
        expect(highTags.length).toBeGreaterThan(0);
        expect(mediumTags.length).toBeGreaterThan(0);
        expect(lowTags.length).toBeGreaterThan(0);
      });
    });

    it('应该显示不同状态标签', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const pendingTags = screen.queryAllByText('待处理');
        const inProgressTags = screen.queryAllByText('进行中');
        const completedTags = screen.queryAllByText('已完成');
        const overdueTags = screen.queryAllByText('已逾期');

        expect(pendingTags.length).toBeGreaterThan(0);
        expect(inProgressTags.length).toBeGreaterThan(0);
        expect(completedTags.length).toBeGreaterThan(0);
        expect(overdueTags.length).toBeGreaterThan(0);
      });
    });

    it('应该显示不同类型标签', async () => {
      render(<TodosPage />);

      await waitFor(() => {
        const approvalTags = screen.queryAllByText('审批');
        const taskTags = screen.queryAllByText('任务');
        const reminderTags = screen.queryAllByText('提醒');
        const reviewTags = screen.queryAllByText('评审');

        expect(approvalTags.length).toBeGreaterThan(0);
        expect(taskTags.length).toBeGreaterThan(0);
        expect(reminderTags.length).toBeGreaterThan(0);
        expect(reviewTags.length).toBeGreaterThan(0);
      });
    });
  });
});
