import { Alert, Divider, Empty, Space, Typography } from 'antd';
import type { GroupingResultResponse } from '@/types/grouping';
import { ActionButtons } from './ActionButtons';
import { CandidateRules } from './CandidateRules';
import { EvidenceChain } from './EvidenceChain';
import { ResultSummary } from './ResultSummary';

interface GroupingResultPanelProps {
  response: GroupingResultResponse | null;
}

export function GroupingResultPanel({ response }: GroupingResultPanelProps) {
  if (!response) {
    return <Empty description="执行入组后将在这里显示结果和证据链" />;
  }

  if (response.status === 'failed' || !response.result) {
    return (
      <Alert
        type="error"
        showIcon
        message={response.error?.message ?? '入组失败'}
        description={
          <Space direction="vertical">
            <Typography.Text>失败阶段：{response.error?.stage ?? '-'}</Typography.Text>
            <Typography.Text>建议：{response.error?.suggestions.join('；') ?? '请检查输入'}</Typography.Text>
          </Space>
        }
      />
    );
  }

  return (
    <div className="dense-grid">
      <ResultSummary result={response.result} />
      <div>
        <h3 className="section-title">证据链</h3>
        <EvidenceChain evidence={response.result.evidence} />
      </div>
      <div className="muted-panel">
        <h3 className="section-title">自然语言解释</h3>
        <Typography.Paragraph>{response.result.explanation}</Typography.Paragraph>
      </div>
      <div>
        <h3 className="section-title">候选规则</h3>
        <CandidateRules candidates={response.result.candidateRules} />
      </div>
      <Divider />
      <ActionButtons result={response} />
    </div>
  );
}
