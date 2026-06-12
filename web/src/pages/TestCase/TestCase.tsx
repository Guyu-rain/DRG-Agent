import { ExportOutlined, PlayCircleOutlined, SendOutlined } from '@ant-design/icons';
import { Button, Checkbox, Descriptions, Drawer, Form, InputNumber, Select, Space, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { RuleVersionSelector } from '@/pages/DRGGrouping/components/RuleVersionSelector';
import { testcasesApi } from '@/services';
import { useTestcaseStore } from '@/stores/testcaseStore';
import type { ScenarioType, TestCaseItem, TestPriority } from '@/types/testcase';
import { priorityLabels, scenarioLabels } from '@/utils/constants';
import { triggerDownload } from '@/utils/download';
import { formatDateTime } from '@/utils/format';

export function TestCase() {
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
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{detail.testCaseId}</Descriptions.Item>
            <Descriptions.Item label="类型">{scenarioLabels[detail.scenarioType]}</Descriptions.Item>
            <Descriptions.Item label="优先级">{priorityLabels[detail.priority]}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDateTime(detail.createdAt)}</Descriptions.Item>
            <Descriptions.Item label="输入病历">
              <pre>{JSON.stringify(detail.inputCase, null, 2)}</pre>
            </Descriptions.Item>
            <Descriptions.Item label="预期结果">
              <pre>{JSON.stringify(detail.expectedResult, null, 2)}</pre>
            </Descriptions.Item>
            <Descriptions.Item label="实际结果">
              <pre>{detail.actualResult ? JSON.stringify(detail.actualResult, null, 2) : '尚未执行'}</pre>
            </Descriptions.Item>
            <Descriptions.Item label="执行结论">
              {detail.isPassed == null ? '尚未执行' : detail.isPassed ? '通过' : '失败'}
            </Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
    </div>
  );
}
