import { Spin } from 'antd';

export function Loading() {
  return (
    <div className="center-state">
      <Spin size="large" />
    </div>
  );
}
