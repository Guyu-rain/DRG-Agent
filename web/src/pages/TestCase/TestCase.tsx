import { ExportOutlined, PlayCircleOutlined, SendOutlined } from '@ant-design/icons';
import { App, Button, Card, Checkbox, Col, Descriptions, Drawer, Form, InputNumber, Row, Select, Space, Statistic, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { RuleVersionSelector } from '@/pages/DRGGrouping/components/RuleVersionSelector';
import { testcasesApi } from '@/services';
import { useTestcaseStore } from '@/stores/testcaseStore';
import type { ScenarioType, TestCaseItem, TestPriority } from '@/types/testcase';
import { priorityLabels, scenarioLabels } from '@/utils/constants';
import { triggerDownload } from '@/utils/download';
import { formatDateTime } from '@/utils/format';

function renderDiagnosisCode(dx: { code?: string | null; name?: string | null } | null | undefined) {
  if (!dx) return <Typography.Text type="secondary">-</Typography.Text>;
  return (
    <Typography.Text>
      {dx.code ? <Typography.Text code>{dx.code}</Typography.Text> : null}
      {dx.name ? <> {dx.name}</> : null}
    </Typography.Text>
  );
}

function renderInputCase(inputCase: Record<string, unknown> | null | undefined) {
  if (!inputCase || !Object.keys(inputCase).length) {
    return <Typography.Text type="secondary">空病历</Typography.Text>;
  }
  const pd = inputCase.primaryDiagnosis as Record<string, unknown> | null;
  const sd = (inputCase.secondaryDiagnoses as Array<Record<string, unknown>>) || [];
  const pp = inputCase.primaryProcedure as Record<string, unknown> | null;
  const op = (inputCase.otherProcedures as Array<Record<string, unknown>>) || [];

  return (
    <Descriptions column={1} size="small" colon={false}>
      <Descriptions.Item label="主诊断">{renderDiagnosisCode(pd)}</Descriptions.Item>
      <Descriptions.Item label="次要诊断">
        {sd.length > 0
          ? sd.map((d, i) => <div key={i}>{renderDiagnosisCode(d)}</div>)
          : <Typography.Text type="secondary">无</Typography.Text>}
      </Descriptions.Item>
      <Descriptions.Item label="主要手术">{renderDiagnosisCode(pp)}</Descriptions.Item>
      {op.length > 0 ? (
        <Descriptions.Item label="其他手术">
          {op.map((p, i) => <div key={i}>{renderDiagnosisCode(p)}</div>)}
        </Descriptions.Item>
      ) : null}
    </Descriptions>
  );
}

function renderGroupingResult(result: Record<string, unknown> | null | undefined) {
  if (!result || !Object.keys(result).length) {
    return <Typography.Text type="secondary">无结果</Typography.Text>;
  }
  const grouped = result.isGrouped as boolean | null;
  if (grouped === false) {
    return (
      <Space direction="vertical" size={4}>
        <Tag color="red">未入组</Tag>
        {result.stage ? <Typography.Text type="secondary">阶段: {String(result.stage)}</Typography.Text> : null}
        {result.error ? <Typography.Text type="secondary">原因: {String(result.error)}</Typography.Text> : null}
      </Space>
    );
  }
  if (grouped === true) {
    const complication = (result.complication as string) || 'NONE';
    return (
      <Row gutter={[8, 8]}>
        <Col span={8}><Statistic title="MDC" value={String(result.mdc ?? '-')} valueStyle={{ fontSize: 18 }} /></Col>
        <Col span={8}><Statistic title="ADRG" value={String(result.adrg ?? '-')} valueStyle={{ fontSize: 18 }} /></Col>
        <Col span={8}><Statistic title="DRG" value={String(result.drg ?? '-')} valueStyle={{ fontSize: 18 }} /></Col>
        <Col span={24}>
          <Typography.Text type="secondary">并发症等级 </Typography.Text>
          <Tag color={complication === 'MCC' ? 'red' : complication === 'CC' ? 'orange' : 'default'}>{complication}</Tag>
        </Col>
      </Row>
    );
  }
  return <pre style={{ fontSize: 12, margin: 0 }}>{JSON.stringify(result, null, 2)}</pre>;
}

export function TestCase() {
  const { message } = App.useApp();
  const { testcases, isGenerating, generateTestcases, fetchTestcases, setFilter } = useTestcaseStore();
  const [selected, setSelected] = useState<string[]>([]);
  const [detail, setDetail] = useState<TestCaseItem | null>(null);
  const [selectedRuleVersion, setSelectedRuleVersion] = useState<string | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);

  useEffect(() => {
    void fetchTestcases();
  }, [fetchTestcases]);

  const generate = async (values: { scenarioTypes: ScenarioType[]; maxCount: number; mdc: string }) => {
    const ruleVersionId = selectedRuleVersion;
    if (!ruleVersionId) {
      message.error('请先选择规则版本');
      return;
    }
    const taskId = await generateTestcases({
      ruleVersionId,
      scenarioTypes: values.scenarioTypes,
      scope: {
        mdcList: values.mdc === 'ALL' ? [] : [values.mdc],
        includeAllRules: values.mdc === 'ALL',
      },
      maxCount: values.maxCount,
    });
    message.success(`测试用例生成完成：${taskId}`);
  };

  const execute = async (testCaseId: string) => {
    setExecutingId(testCaseId);
    try {
      const response = await testcasesApi.execute(testCaseId);
      await fetchTestcases();
      const updated = await testcasesApi.detail(testCaseId);
      setDetail(updated.data);
      if (response.data.isPassed) {
        message.success('测试用例执行通过');
      } else {
        message.warning('测试用例执行完成，但实际结果与预期不一致');
      }
    } finally {
      setExecutingId(null);
    }
  };

  const exportSelected = async () => {
    if (!selected.length) {
      message.warning('请先选择要导出的测试用例');
      return;
    }
    const response = await testcasesApi.export(selected);
    triggerDownload(response.data.downloadUrl);
    message.success('导出文件已开始下载');
  };

  const submitSelected = async () => {
    if (!selected.length) {
      message.warning('请先选择要提交的测试用例');
      return;
    }
    await testcasesApi.submitToDocuments(selected);
    message.success('已提交到文档系统');
  };

  return (
    <div>
      <PageHeader title="测试用例管理" description="生成、筛选、执行和导出 DRG 入组测试用例。" />
      <div className="two-column">
        <section className="content-band">
          <h3 className="section-title">生成配置</h3>
          <Form
            layout="vertical"
            initialValues={{ scenarioTypes: ['normal', 'boundary', 'abnormal'], maxCount: 50, mdc: 'ALL' }}
            onFinish={(values) => void generate(values)}
          >
            <Form.Item label="规则版本" name="ruleVersionId">
              <RuleVersionSelector value={selectedRuleVersion} onChange={setSelectedRuleVersion} />
            </Form.Item>
            <Form.Item label="场景类型" name="scenarioTypes">
              <Checkbox.Group
                options={[
                  { value: 'normal', label: '正常' },
                  { value: 'boundary', label: '边界' },
                  { value: 'abnormal', label: '异常' },
                ]}
              />
            </Form.Item>
            <Form.Item label="范围" name="mdc">
              <Select
                options={[
                  { value: 'ALL', label: '全部规则' },
                  { value: 'MDCB', label: 'MDCB 神经系统' },
                  { value: 'MDCE', label: 'MDCE 呼吸系统' },
                  { value: 'MDCG', label: 'MDCG 消化系统' },
                  { value: 'MDCH', label: 'MDCH 肝胆胰系统' },
                ]}
              />
            </Form.Item>
            <Form.Item label="数量上限" name="maxCount">
              <InputNumber min={1} max={200} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={isGenerating}>
              生成用例
            </Button>
          </Form>
        </section>
        <section className="content-band">
          <Space style={{ marginBottom: 16 }} wrap>
            <Select
              allowClear
              placeholder="全部场景"
              style={{ width: 140 }}
              onChange={(scenarioType?: ScenarioType) => {
                setFilter({ scenarioType });
                void fetchTestcases();
              }}
              options={Object.entries(scenarioLabels).map(([value, label]) => ({ value, label }))}
            />
            <Button icon={<ExportOutlined />} onClick={() => void exportSelected()}>
              导出选中
            </Button>
            <Button icon={<SendOutlined />} onClick={() => void submitSelected()}>
              提交到文档系统
            </Button>
          </Space>
          <Table
            rowKey="testCaseId"
            dataSource={testcases}
            rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys.map(String)) }}
            pagination={false}
            columns={[
              { title: 'ID', dataIndex: 'testCaseId', width: 120 },
              { title: '标题', dataIndex: 'title' },
              {
                title: '类型',
                dataIndex: 'scenarioType',
                width: 100,
                render: (value: ScenarioType) => <Tag color={value === 'normal' ? 'green' : value === 'boundary' ? 'orange' : 'red'}>{scenarioLabels[value]}</Tag>,
              },
              {
                title: '优先级',
                dataIndex: 'priority',
                width: 90,
                render: (value: TestPriority) => priorityLabels[value],
              },
              {
                title: '结果',
                dataIndex: 'isPassed',
                width: 90,
                render: (value: boolean | null | undefined) =>
                  value == null ? <Tag>未执行</Tag> : value ? <Tag color="green">通过</Tag> : <Tag color="red">失败</Tag>,
              },
              {
                title: '操作',
                width: 170,
                render: (_, record) => (
                  <Space>
                    <Button size="small" onClick={() => setDetail(record)}>
                      详情
                    </Button>
                    <Button
                      size="small"
                      icon={<PlayCircleOutlined />}
                      loading={executingId === record.testCaseId}
                      onClick={() => void execute(record.testCaseId)}
                    >
                      执行
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </section>
      </div>
      <Drawer open={!!detail} title={detail?.title} width={560} onClose={() => setDetail(null)}>
        {detail ? (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="ID">{detail.testCaseId}</Descriptions.Item>
              <Descriptions.Item label="类型">{scenarioLabels[detail.scenarioType]}</Descriptions.Item>
              <Descriptions.Item label="优先级">{priorityLabels[detail.priority]}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDateTime(detail.createdAt)}</Descriptions.Item>
            </Descriptions>

            <h4 style={{ marginBottom: 8 }}>输入病历</h4>
            <Card size="small" style={{ marginBottom: 16 }}>
              {renderInputCase(detail.inputCase)}
            </Card>

            <h4 style={{ marginBottom: 8 }}>分组结果</h4>
            <Row gutter={[12, 12]}>
              <Col xs={24} sm={detail.actualResult ? 12 : 24}>
                <Card size="small" title="预期结果">
                  {renderGroupingResult(detail.expectedResult)}
                </Card>
              </Col>
              {detail.actualResult ? (
                <Col xs={24} sm={12}>
                  <Card size="small" title="实际结果">
                    {renderGroupingResult(detail.actualResult)}
                  </Card>
                </Col>
              ) : null}
            </Row>

            <div style={{ marginTop: 16 }}>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="执行结论">
                  {detail.isPassed == null ? (
                    <Tag>尚未执行</Tag>
                  ) : detail.isPassed ? (
                    <Tag color="green">通过</Tag>
                  ) : (
                    <Tag color="red">失败</Tag>
                  )}
                </Descriptions.Item>
                {detail.expectedExplanation ? (
                  <Descriptions.Item label="说明">
                    <Typography.Text>{detail.expectedExplanation}</Typography.Text>
                  </Descriptions.Item>
                ) : null}
              </Descriptions>
            </div>
          </>
        ) : null}
      </Drawer>
    </div>
  );
}
