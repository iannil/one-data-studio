/**
 * PageWrapper 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock antd Card
vi.mock('antd', () => ({
  Card: ({ children, title, extra, bordered, style }: any) => (
    <div
      data-testid="card"
      data-bordered={bordered}
      style={style}
    >
      {title && <div data-testid="card-title">{title}</div>}
      {extra && <div data-testid="card-extra">{extra}</div>}
      <div data-testid="card-content">{children}</div>
    </div>
  ),
}));

import PageWrapper from './PageWrapper';

describe('PageWrapper Component', () => {
  it('should render children content', () => {
    render(
      <PageWrapper>
        <p>Test content</p>
      </PageWrapper>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should render with title', () => {
    render(
      <PageWrapper title="Page Title">
        <p>Content</p>
      </PageWrapper>
    );

    expect(screen.getByTestId('card-title')).toHaveTextContent('Page Title');
  });

  it('should render without title when not provided', () => {
    render(
      <PageWrapper>
        <p>Content</p>
      </PageWrapper>
    );

    expect(screen.queryByTestId('card-title')).not.toBeInTheDocument();
  });

  it('should render extra content', () => {
    const ExtraButton = () => <button>Action</button>;

    render(
      <PageWrapper title="Page" extra={<ExtraButton />}>
        <p>Content</p>
      </PageWrapper>
    );

    expect(screen.getByTestId('card-extra')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  it('should render without extra when not provided', () => {
    render(
      <PageWrapper title="Page">
        <p>Content</p>
      </PageWrapper>
    );

    expect(screen.queryByTestId('card-extra')).not.toBeInTheDocument();
  });

  it('should apply custom style', () => {
    render(
      <PageWrapper style={{ backgroundColor: 'red' }}>
        <p>Content</p>
      </PageWrapper>
    );

    const card = screen.getByTestId('card');
    expect(card).toHaveStyle({ borderRadius: '8px' });
  });

  it('should render card without border', () => {
    render(
      <PageWrapper>
        <p>Content</p>
      </PageWrapper>
    );

    const card = screen.getByTestId('card');
    expect(card).toHaveAttribute('data-bordered', 'false');
  });

  it('should render complex children', () => {
    render(
      <PageWrapper title="Complex Page">
        <div>
          <h1>Header</h1>
          <ul>
            <li>Item 1</li>
            <li>Item 2</li>
          </ul>
        </div>
      </PageWrapper>
    );

    expect(screen.getByText('Header')).toBeInTheDocument();
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
  });

  it('should render multiple children', () => {
    render(
      <PageWrapper>
        <p>First paragraph</p>
        <p>Second paragraph</p>
      </PageWrapper>
    );

    expect(screen.getByText('First paragraph')).toBeInTheDocument();
    expect(screen.getByText('Second paragraph')).toBeInTheDocument();
  });

  it('should render with extra button and title together', () => {
    render(
      <PageWrapper
        title="Dashboard"
        extra={<button>Refresh</button>}
      >
        <div>Dashboard content</div>
      </PageWrapper>
    );

    expect(screen.getByTestId('card-title')).toHaveTextContent('Dashboard');
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument();
    expect(screen.getByText('Dashboard content')).toBeInTheDocument();
  });
});
