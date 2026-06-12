import { Button, Card, Col, Drawer, Row, Select, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { usePolling } from '@/hooks/usePolling';
import { tasksApi } from '@/services';
import { useTaskStore } from '@/stores/taskStore';
import type { TaskStep, TaskSummary } from '@/types/task';
import { formatDateTime, formatDuration, taskStatusColor, taskStatusText } from '@/utils/format';

export function TaskCenter() {
  const { tasks, fetchTasks } = useTaskStore();
  const [status, setStatus] = useState<string>();
  const [detail, setDetail] = useState<(TaskSummary & { steps: TaskStep[] }) | null>(null);

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  const refresh = useCallback(() => fetchTasks(), [fetchTasks]);
  const hasActiveTasks = tasks.some((task) => ['pending', 'running', 'executing'].includes(task.status));
  usePolling(refresh, 1500, hasActiveTasks);

  const filtered = useMemo(() => tasks.filter((task) => !status || task.status === status), [status, tasks]);
  const stats = useMemo(
    () => ({
      total: tasks.length,
      running: tasks.filter((task) => ['running', 'executing', 'pending'].includes(task.status)).length,
      completed: tasks.filter((task) => task.status === 'completed').length,
      failed: tasks.filter((task) => task.status === 'failed').length,
    }),
    [tasks],
  );

  const openDetail = async (task: TaskSummary) => {
    const response = await tasksApi.detail(task.taskId);
    setDetail(response.data);
  };

  const cancel = async (taskId: string) => {
    await tasksApi.cancel(taskId);
    if (detail?.taskId === taskId) setDetail(null);
    await fetchTasks();
    message.success('任务已取消');
  };

  return (
    <div>
      <PageHeader
        title="任务中心"
        description="集中查看入组、文档和测试任务的状态、耗时与步骤详情。"
        extra={
          <Select
            allowClear
            placeholder="按状态筛选"
            style={{ width: 160 }}
            value={status}
            onChange={setStatus}
            options={[
              { value: 'completed', label: '已完成' },
              { value: 'failed', label: '失败' },
              { value: 'running', label: '运行中' },
              { value: 'cancelled', label: '已取消' },
            ]}
          />
        }
      />
      <div className="metric-grid">
        <Card>
          <Statistic title="总任务数" value={stats.total} />
        </Card>
        <Card>
          <Statistic title="执行中" value={stats.running} />
        </Card>
        <Card>
          <Statistic title="已完成" value={stats.completed} />
        </Card>
        <Card>
          <Statistic title="失败" value={stats.failed} />
        </Card>
      </div>
      <div className="content-band" style={{ marginTop: 20 }}>
        <Table
          rowKey="taskId"
          dataSource={filtered}
          pagination={false}
          columns={[
            { title: '任务', dataIndex: 'title' },
            { title: '类型', dataIndex: 'type', width: 120 },
            {
              title: '状态',
              dataIndex: 'status',
              width: 120,
              render: (value) => <Tag color={taskStatusColor(value)}>{taskStatusText(value)}</Tag>,
            },
            { title: '创建时间', dataIndex: 'createdAt', render: formatDateTime },
            { title: '耗时', dataIndex: 'durationMs', render: formatDuration },
            {
              title: '操作',
              width: 160,
              render: (_, record) => (
                <Space>
                  <Button size="small" onClick={() => void openDetail(record)}>
                    详情
                  </Button>
                  {['pending', 'running', 'executing'].includes(record.status) ? (
                    <Button size="small" danger onClick={() => void cancel(record.taskId)}>
                      取消
                    </Button>
                  ) : null}
                </Space>
              ),
            },
          ]}
        />
      </div>
      <Drawer open={!!detail} title={detail?.title} width={520} onClose={() => setDetail(null)}>
        <Typography.Paragraph type="secondary">
          任务 ID：{detail?.taskId}，耗时：{formatDuration(detail?.durationMs)}
        </Typography.Paragraph>
        <Row gutter={[12, 12]}>
          {detail?.steps.map((step) => (
            <Col span={24} key={step.stepName}>
              <Card size="small">
                <Space direction="vertical">
                  <Typography.Text strong>
                    {step.stepOrder}. {step.stepName}
                  </Typography.Text>
                  <Tag color={taskStatusColor(step.status)}>{taskStatusText(step.status)}</Tag>
                  <Typography.Text type="secondary">耗时：{formatDuration(step.durationMs)}</Typography.Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </Drawer>
    </div>
  );
}
