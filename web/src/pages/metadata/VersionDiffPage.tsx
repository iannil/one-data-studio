/**
 * 元数据版本对比页面
 */

import { Card } from 'antd';
import { MetadataVersionDiff } from '@/components/metadata';

function MetadataVersionDiffPage() {
  return (
    <div style={{ padding: '24px' }}>
      <MetadataVersionDiff />
    </div>
  );
}

export default MetadataVersionDiffPage;
