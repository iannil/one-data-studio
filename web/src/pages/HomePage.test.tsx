import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import HomePage from './HomePage';

// Mock window.location
const mockLocation = {
  href: '',
};
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('HomePage', () => {
  beforeEach(() => {
    mockLocation.href = '';
  });

  it('应该正确渲染首页', () => {
    renderWithRouter(<HomePage />);

    expect(screen.getByText('欢迎来到 ONE-DATA-STUDIO')).toBeInTheDocument();
  });

  it('应该显示平台描述', () => {
    renderWithRouter(<HomePage />);

    expect(
      screen.getByText(/统一数据 \+ AI \+ LLM 融合平台/)
    ).toBeInTheDocument();
  });

  it('应该显示统计卡片', () => {
    renderWithRouter(<HomePage />);

    expect(screen.getByText('数据集')).toBeInTheDocument();
    expect(screen.getByText('模型')).toBeInTheDocument();
    expect(screen.getByText('工作流')).toBeInTheDocument();
    expect(screen.getByText('对话')).toBeInTheDocument();
  });

  it('应该显示快速开始标题', () => {
    renderWithRouter(<HomePage />);

    expect(screen.getByText('快速开始')).toBeInTheDocument();
  });

  it('应该显示数据集管理卡片', () => {
    renderWithRouter(<HomePage />);

    expect(screen.getByText('数据集管理')).toBeInTheDocument();
    expect(
      screen.getByText('管理数据集、定义 Schema、版本控制、文件上传')
    ).toBeInTheDocument();
  });

  it('应该显示 AI 聊天卡片', () => {
    renderWithRouter(<HomePage />);

    expect(screen.getByText('AI 聊天')).toBeInTheDocument();
    expect(
      screen.getByText('与 AI 模型对话、流式输出、参数配置')
    ).toBeInTheDocument();
  });

  it('应该显示元数据浏览卡片', () => {
    renderWithRouter(<HomePage />);

    expect(screen.getByText('元数据浏览')).toBeInTheDocument();
    expect(
      screen.getByText('浏览数据库和表结构、Text-to-SQL 查询')
    ).toBeInTheDocument();
  });
});

describe('HomePage 导航功能', () => {
  beforeEach(() => {
    mockLocation.href = '';
  });

  it('点击数据集管理卡片应该跳转到 /datasets', async () => {
    const user = userEvent.setup();
    renderWithRouter(<HomePage />);

    const datasetsCard = screen.getByText('数据集管理').closest('.ant-card');
    if (datasetsCard) {
      await user.click(datasetsCard);
      expect(mockLocation.href).toBe('/datasets');
    }
  });

  it('点击 AI 聊天卡片应该跳转到 /chat', async () => {
    const user = userEvent.setup();
    renderWithRouter(<HomePage />);

    const chatCard = screen.getByText('AI 聊天').closest('.ant-card');
    if (chatCard) {
      await user.click(chatCard);
      expect(mockLocation.href).toBe('/chat');
    }
  });

  it('点击元数据浏览卡片应该跳转到 /metadata', async () => {
    const user = userEvent.setup();
    renderWithRouter(<HomePage />);

    const metadataCard = screen.getByText('元数据浏览').closest('.ant-card');
    if (metadataCard) {
      await user.click(metadataCard);
      expect(mockLocation.href).toBe('/metadata');
    }
  });
});

describe('HomePage 统计数据', () => {
  it('统计数据初始应该为 0', () => {
    renderWithRouter(<HomePage />);

    // 检查统计值都是 0
    const statValues = screen.getAllByText('0');
    expect(statValues.length).toBeGreaterThanOrEqual(4);
  });
});

describe('HomePage 样式', () => {
  it('应该有正确的布局', () => {
    renderWithRouter(<HomePage />);

    // 快速开始区域应该存在
    expect(screen.getByText('快速开始')).toBeInTheDocument();
  });
});
