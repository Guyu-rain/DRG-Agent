import { Button, Result, Typography } from 'antd';

interface ErrorFallbackProps {
  error?: Error;
  onReset?: () => void;
}

/** 错误边界的兜底界面。 */
export function ErrorFallback({ error, onReset }: ErrorFallbackProps) {
  return (
    <Result
      status="error"
      title="页面加载失败"
      subTitle="页面在渲染过程中发生异常，可尝试重试或刷新页面。"
      extra={[
        <Button key="retry" type="primary" onClick={onReset ?? (() => window.location.reload())}>
          重试
        </Button>,
        <Button key="reload" onClick={() => window.location.reload()}>
          刷新页面
        </Button>,
      ]}
    >
      {error ? (
        <Typography.Paragraph type="secondary" style={{ whiteSpace: 'pre-wrap' }}>
          {error.message}
        </Typography.Paragraph>
      ) : null}
    </Result>
  );
}
