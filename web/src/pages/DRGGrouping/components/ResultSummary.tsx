import { Card, Col, Row, Statistic, Tag, Typography } from 'antd';
import type { GroupingResult } from '@/types/grouping';

interface ResultSummaryProps {
  result: GroupingResult;
}

export function ResultSummary({ result }: ResultSummaryProps) {
  return (
    <Card className="result-summary-card">
      <Row gutter={[16, 16]}>
        <Col xs={24} md={10}>
          <Statistic title="最终 DRG" value={result.drg.code} />
          <Typography.Text strong>{result.drg.name}</Typography.Text>
        </Col>
        <Col xs={8} md={4}>
          <Statistic title="MDC" value={result.mdc.code} />
        </Col>
        <Col xs={8} md={4}>
          <Statistic title="ADRG" value={result.adrg.code} />
        </Col>
        <Col xs={8} md={6}>
          <Typography.Text type="secondary">并发症等级</Typography.Text>
          <div>
            <Tag color={result.complication === 'MCC' ? 'red' : result.complication === 'CC' ? 'orange' : 'default'}>
              {result.complication}
            </Tag>
          </div>
        </Col>
      </Row>
    </Card>
  );
}
