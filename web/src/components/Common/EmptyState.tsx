import { Empty } from 'antd';

interface EmptyStateProps {
  description?: string;
}

export function EmptyState({ description = '暂无数据' }: EmptyStateProps) {
  return (
    <div className="center-state">
      <Empty description={description} />
    </div>
  );
}
