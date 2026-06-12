import { Modal, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { testcasesApi } from '@/services';
import type { ScenarioType, TestCaseItem } from '@/types/testcase';
import { scenarioLabels } from '@/utils/constants';

interface TestCaseImportModalProps {
  open: boolean;
  onClose: () => void;
  onImport: (testCase: TestCaseItem) => void;
}

export function TestCaseImportModal({ open, onClose, onImport }: TestCaseImportModalProps) {
  const [testcases, setTestcases] = useState<TestCaseItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setSelectedId(undefined);
    testcasesApi
      .list({ page: 1, pageSize: 200 })
      .then((response) => setTestcases(response.data.items))
      .catch(() => message.error('测试用例加载失败'))
      .finally(() => setLoading(false));
  }, [open]);

  const selected = testcases.find((item) => item.testCaseId === selectedId);

  return (
    <Modal
      open={open}
      title="导入测试用例"
      okText="导入到文本模式"
      cancelText="取消"
      okButtonProps={{ disabled: !selected }}
      onCancel={onClose}
      onOk={() => {
        if (selected) onImport(selected);
      }}
      width={760}
    >
      <Table
        rowKey="testCaseId"
        loading={loading}
        dataSource={testcases}
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
        rowSelection={{
          type: 'radio',
          selectedRowKeys: selectedId ? [selectedId] : [],
          onChange: (keys) => setSelectedId(keys[0] ? String(keys[0]) : undefined),
        }}
        onRow={(record) => ({ onClick: () => setSelectedId(record.testCaseId) })}
        columns={[
          { title: 'ID', dataIndex: 'testCaseId', width: 150 },
          { title: '标题', dataIndex: 'title' },
          {
            title: '类型',
            dataIndex: 'scenarioType',
            width: 90,
            render: (value: ScenarioType) => <Tag>{scenarioLabels[value]}</Tag>,
          },
          {
            title: '预期 DRG',
            width: 110,
            render: (_, record) => String(record.expectedResult.drg ?? '-'),
          },
        ]}
      />
    </Modal>
  );
}
