import { DownloadOutlined, SendOutlined } from '@ant-design/icons';
import { Button, message, Space } from 'antd';
import { useState } from 'react';
import { useGroupingStore } from '@/stores/groupingStore';
import type { GroupingResultResponse } from '@/types/grouping';
import { downloadJson } from '@/utils/download';
import { buildGroupingResultExport } from '@/utils/groupingData';

interface ActionButtonsProps {
  result: GroupingResultResponse;
}

export function ActionButtons({ result }: ActionButtonsProps) {
  const [reviewLoading, setReviewLoading] = useState(false);
  const { currentCase, submitForReview } = useGroupingStore();

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

  const handleSaveResult = () => {
    try {
      if (!currentCase) throw new Error('当前病历信息不存在');
      downloadJson(buildGroupingResultExport(result, currentCase), `drg_result_${result.taskId}.json`);
      message.success('入组结果已保存');
    } catch (e) {
      message.error(e instanceof Error ? e.message : '入组结果保存失败');
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
        icon={<DownloadOutlined />}
        disabled={!hasResult}
        onClick={handleSaveResult}
      >
        保存结果
      </Button>
    </Space>
  );
}
