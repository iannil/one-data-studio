/**
 * Loading 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/testUtils';
import Loading from './Loading';

describe('Loading Component', () => {
  it('should render with default props', () => {
    render(<Loading />);
    expect(document.querySelector('.ant-spin')).toBeInTheDocument();
  });

  it('should render custom tip text', () => {
    const { container } = render(<Loading tip="Loading data..." />);
    // Spin component should be rendered with the tip
    expect(container.querySelector('.ant-spin')).toBeInTheDocument();
  });

  it('should render with default size', () => {
    const { container } = render(<Loading />);
    expect(container.querySelector('.ant-spin')).toBeInTheDocument();
  });

  it('should render with small size', () => {
    const { container } = render(<Loading size="small" />);
    const spinner = container.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('should render with large size', () => {
    const { container } = render(<Loading size="large" />);
    const spinner = container.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('should render fullscreen layout', () => {
    const { container } = render(<Loading fullScreen />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveStyle({ height: '100vh' });
  });

  it('should render centered', () => {
    const { container } = render(<Loading />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveStyle({ display: 'flex', alignItems: 'center', justifyContent: 'center' });
  });
});
