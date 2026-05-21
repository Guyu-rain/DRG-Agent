import { Input, Select, Table, Tag } from 'antd';
import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { useTaskStore } from '@/stores/taskStore';
import type { ExecutionLog as ExecutionLogItem } from '@/types/task';
import { formatDateTime } from '@/utils/format';

const levelColor: Record<ExecutionLogItem['level'], string> = {
  debug: 'default',
  info: 'blue',
  warning: 'orange',
  error: 'red',
};

export function ExecutionLog() {
  const { logs, fetchLogs } = useTaskStore();
  const [level, setLevel] = useState<string>();
  const [taskId, setTaskId] = useState('');

  useEffect(() => {
    void fetchLogs({ level, taskId: taskId || undefined });
  }, [fetchLogs, level, taskId]);

  return (
    <div>
      <PageHeader title="执行日志" description="按时间倒序查看智能体与规则引擎的输入、输出和错误信息。" />
      <div className="content-band">
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <Select
            allowClear
            placeholder="日志级别"
            style={{ width: 140 }}
            value={level}
            onChange={setLevel}
            options={[
              { value: 'info', label: 'info' },
              { value: 'warning', label: 'warning' },
              { value: 'error', label: 'error' },
            ]}
          />
          <Input.Search placeholder="任务 ID" allowClear value={taskId} onChange={(event) => setTaskId(event.target.value)} />
        </div>
        <Table
          rowKey="logId"
          dataSource={logs}
          pagination={false}
          expandable={{
            expandedRowRender: (record) => (
              <pre>
                {JSON.stringify(
                  {
                    input: record.inputSummary,
                    output: record.outputSummary,
                    error: record.errorDetail,
                  },
                  null,
                  2,
                )}
              </pre>
            ),
          }}
          columns={[
            { title: '时间', dataIndex: 'timestamp', render: formatDateTime, width: 170 },
            {
              title: '级别',
              dataIndex: 'level',
              render: (value: ExecutionLogItem['level']) => <Tag color={levelColor[value]}>{value}</Tag>,
              width: 100,
            },
            { title: '智能体', dataIndex: 'agent', width: 180 },
            { title: '任务 ID', dataIndex: 'taskId', width: 210 },
            { title: '消息', dataIndex: 'message' },
          ]}
        />
      </div>
    </div>
  );
}
