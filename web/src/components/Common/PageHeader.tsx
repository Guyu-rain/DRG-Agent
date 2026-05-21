import { Space, Typography } from 'antd';
import type { ReactNode } from 'react';
import './PageHeader.css';

interface PageHeaderProps {
  title: string;
  description?: string;
  extra?: ReactNode;
}

export function PageHeader({ title, description, extra }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div>
        <Typography.Title level={2}>{title}</Typography.Title>
        {description ? <Typography.Paragraph type="secondary">{description}</Typography.Paragraph> : null}
      </div>
      {extra ? <Space>{extra}</Space> : null}
    </div>
  );
}
