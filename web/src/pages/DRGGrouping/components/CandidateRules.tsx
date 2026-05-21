import { List, Tag, Typography } from 'antd';
import type { CandidateRule } from '@/types/grouping';

interface CandidateRulesProps {
  candidates: CandidateRule[];
}

export function CandidateRules({ candidates }: CandidateRulesProps) {
  return (
    <List
      size="small"
      dataSource={candidates}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta
            title={
              <Typography.Text strong>
                {item.adrg} → {item.drg} {item.name}
              </Typography.Text>
            }
            description={item.reason}
          />
          <Tag color={item.reason.includes('命中') && !item.reason.includes('未命中') ? 'green' : 'default'}>
            {item.reason.includes('命中') && !item.reason.includes('未命中') ? '命中' : '未命中'}
          </Tag>
        </List.Item>
      )}
    />
  );
}
