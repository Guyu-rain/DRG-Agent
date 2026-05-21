import { Alert } from 'antd';

export function ErrorFallback() {
  return <Alert type="error" showIcon message="页面加载失败" description="请刷新页面或稍后再试。" />;
}
