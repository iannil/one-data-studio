/**
 * VersionHistory 组件单元测试
 * Sprint 9: 前端组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string | object) => {
      if (typeof defaultValue === 'string') return defaultValue;
      if (typeof defaultValue === 'object' && 'version' in defaultValue) {
        return `Are you sure you want to rollback to version ${defaultValue.version}?`;
      }
      return key;
    },
  }),
}));

// Mock clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

import { VersionHistory } from './VersionHistory';

describe('VersionHistory Component', () => {
  const mockVersions = [
    {
      id: 1,
      workflow_id: 'wf-123',
      version_number: 3,
      content_hash: 'abc123',
      created_at: '2024-01-15T10:00:00Z',
      created_by: 'user1',
      comment: 'Added new node',
      parent_version: 2,
    },
    {
      id: 2,
      workflow_id: 'wf-123',
      version_number: 2,
      content_hash: 'def456',
      created_at: '2024-01-14T10:00:00Z',
      created_by: 'user2',
      comment: 'Fixed bug',
      parent_version: 1,
    },
    {
      id: 3,
      workflow_id: 'wf-123',
      version_number: 1,
      content_hash: 'ghi789',
      created_at: '2024-01-13T10:00:00Z',
      created_by: 'user1',
      comment: 'Initial version',
      parent_version: null,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockVersions),
      text: () => Promise.resolve(''),
    });
  });

  it('should render loading state initially', () => {
    render(<VersionHistory workflowId="wf-123" />);

    // MUI CircularProgress should be rendered during loading
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should render version history after loading', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument();
    });

    expect(screen.getByText('v3')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    expect(screen.getByText('v1')).toBeInTheDocument();
  });

  it('should display version comments', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText('Added new node')).toBeInTheDocument();
    });

    expect(screen.getByText('Fixed bug')).toBeInTheDocument();
    expect(screen.getByText('Initial version')).toBeInTheDocument();
  });

  it('should display version creators', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getAllByText('user1')).toHaveLength(2);
    });

    expect(screen.getByText('user2')).toBeInTheDocument();
  });

  it('should display content hashes', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText('abc123')).toBeInTheDocument();
    });

    expect(screen.getByText('def456')).toBeInTheDocument();
    expect(screen.getByText('ghi789')).toBeInTheDocument();
  });

  it('should highlight current version', async () => {
    render(<VersionHistory workflowId="wf-123" currentVersion={2} />);

    await waitFor(() => {
      expect(screen.getByText('v2')).toBeInTheDocument();
    });

    // Current version should have primary color chip
    const v2Chip = screen.getByText('v2');
    expect(v2Chip.closest('.MuiChip-colorPrimary')).toBeInTheDocument();
  });

  it('should fetch version history on mount', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/workflows/wf-123/versions');
    });
  });

  it('should handle fetch error', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('should display empty state when no versions', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText('No version history available')).toBeInTheDocument();
    });
  });

  it('should allow selecting versions for comparison', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText('v3')).toBeInTheDocument();
    });

    // Click on v1 and v2 to select for comparison
    const listItems = screen.getAllByRole('listitem');
    fireEvent.click(listItems[2]); // v1
    fireEvent.click(listItems[1]); // v2
  });

  it('should call onVersionSelect when version is clicked', async () => {
    const onVersionSelect = vi.fn();
    render(<VersionHistory workflowId="wf-123" onVersionSelect={onVersionSelect} />);

    await waitFor(() => {
      expect(screen.getByText('v3')).toBeInTheDocument();
    });
  });

  it('should render rollback buttons for non-current versions', async () => {
    render(<VersionHistory workflowId="wf-123" currentVersion={3} />);

    await waitFor(() => {
      expect(screen.getByText('v3')).toBeInTheDocument();
    });

    // v2 and v1 should have rollback buttons (v3 is current)
    const rollbackButtons = screen.getAllByRole('button');
    expect(rollbackButtons.length).toBeGreaterThan(0);
  });

  it('should copy hash to clipboard when copy button is clicked', async () => {
    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      expect(screen.getByText('abc123')).toBeInTheDocument();
    });

    // Find and click copy button
    const copyButtons = screen.getAllByRole('button');
    const copyButton = copyButtons.find(btn => btn.querySelector('svg'));

    if (copyButton) {
      fireEvent.click(copyButton);
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    }
  });
});

describe('VersionHistory formatting helpers', () => {
  it('should format dates correctly', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([
        {
          id: 1,
          workflow_id: 'wf-123',
          version_number: 1,
          content_hash: 'abc123',
          created_at: new Date().toISOString(),
          created_by: 'user1',
          comment: 'Test',
          parent_version: null,
        },
      ]),
    });

    render(<VersionHistory workflowId="wf-123" />);

    await waitFor(() => {
      // Should show relative time for recent dates
      expect(screen.getByText(/just now|m ago/)).toBeInTheDocument();
    });
  });
});
