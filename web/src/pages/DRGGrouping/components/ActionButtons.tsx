import {
  ExperimentOutlined,
  FileTextOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { Button, message, Space } from 'antd';
import { useState } from 'react';
import { useGroupingStore } from '@/stores/groupingStore';
import type { GroupingResultResponse } from '@/types/grouping';

interface ActionButtonsProps {
  result: GroupingResultResponse;
}

export function ActionButtons({ result }: ActionButtonsProps) {
  const [reviewLoading, setReviewLoading] = useState(false);
  const [docLoading, setDocLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const { submitForReview, generateDocument, generateTestcases } = useGroupingStore();

  const handleReview = async () => {
    setReviewLoading(true);
    try {
      await submitForReview();
      message.success('已提交复核');
    } catch (e) {
      message.error(e instanceof Error ? e.message : '提交复核失败');
    } finally {
      setReviewLoading(false);
    }
  };

  const handleGenerateDoc = async () => {
    setDocLoading(true);
    try {
      const taskId = await generateDocument('requirements');
      message.success(`文档生成任务已创建：${taskId}`);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '文档生成失败');
    } finally {
      setDocLoading(false);
    }
  };

  const handleGenerateTest = async () => {
    setTestLoading(true);
    try {
      const taskId = await generateTestcases();
      message.success(`测试用例生成任务已创建：${taskId}`);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '测试用例生成失败');
    } finally {
      setTestLoading(false);
    }
  };

  const hasResult = result.status === 'completed' && result.result !== null;

  return (
    <Space wrap>
      <Button
        icon={<SendOutlined />}
        loading={reviewLoading}
        disabled={!hasResult}
        onClick={handleReview}
      >
        提交复核
      </Button>
      <Button
        icon={<FileTextOutlined />}
        loading={docLoading}
        disabled={!hasResult}
        onClick={handleGenerateDoc}
      >
        生成文档
      </Button>
      <Button
        icon={<ExperimentOutlined />}
        loading={testLoading}
        disabled={!hasResult}
        onClick={handleGenerateTest}
      >
        生成测试
      </Button>
    </Space>
  );
}
