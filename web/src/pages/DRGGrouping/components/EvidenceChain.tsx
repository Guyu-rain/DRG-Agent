import { Timeline, Tag, Typography } from 'antd';
import type { EvidenceItem } from '@/types/grouping';

interface EvidenceChainProps {
  evidence: EvidenceItem[];
}

export function EvidenceChain({ evidence }: EvidenceChainProps) {
  return (
    <Timeline
      items={evidence.map((item) => ({
        color: item.excluded ? 'red' : item.ccLevel === 'MCC' ? 'orange' : 'blue',
        children: (
          <div>
            <Tag color="blue">Step {item.step}</Tag>
            <Typography.Text>{item.description}</Typography.Text>
          </div>
        ),
      }))}
    />
  );
}
