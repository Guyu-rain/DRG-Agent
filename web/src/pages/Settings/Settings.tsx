import { Button, Card, Col, Form, Input, InputNumber, Row, Tag, message } from 'antd';
import { useEffect } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { useSettingsStore } from '@/stores/settingsStore';
import type { SystemConfig } from '@/types/task';

export function Settings() {
  const { config, health, fetchConfig, fetchHealth, saveConfig, initDemo } = useSettingsStore();
  const [form] = Form.useForm<SystemConfig>();

  useEffect(() => {
    void Promise.all([fetchConfig(), fetchHealth()]);
  }, [fetchConfig, fetchHealth]);

  useEffect(() => {
    if (config) form.setFieldsValue(config);
  }, [config, form]);

  const save = async () => {
    const values = await form.validateFields();
    await saveConfig(values);
    message.success('配置已保存');
  };

  return (
    <div>
      <PageHeader
        title="系统配置"
        description="配置 LLM、存储路径、活跃规则版本，并查看系统健康状态。"
        extra={<Button onClick={() => void initDemo().then((msg) => message.success(msg))}>初始化演示数据</Button>}
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={15}>
          <div className="content-band">
            <Form form={form} layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="API Base" name={['llm', 'apiBase']}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="模型" name={['llm', 'model']}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="最大重试次数" name={['llm', 'maxRetries']}>
                    <InputNumber min={0} max={10} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="超时秒数" name={['llm', 'timeoutSeconds']}>
                    <InputNumber min={5} max={300} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="文档存储路径" name={['storage', 'documentPath']}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="规则数据路径" name={['storage', 'ruleDataPath']}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="当前活跃规则版本" name={['rules', 'activeRuleVersionId']}>
                    <Input />
                  </Form.Item>
                </Col>
              </Row>
              <Button type="primary" onClick={() => void save()}>
                保存配置
              </Button>
            </Form>
          </div>
        </Col>
        <Col xs={24} lg={9}>
          <Card title="健康检查">
            <p>
              服务状态：
              <Tag color={health?.status === 'healthy' ? 'green' : 'orange'}>{health?.status ?? '-'}</Tag>
            </p>
            <p>数据库：{health?.components?.database ?? '-'}</p>
            <p>Redis：{health?.components?.redis ?? '-'}</p>
            <p>Celery：{health?.components?.celery ?? '-'}</p>
            <p>LLM API：{health?.components?.llm_api ?? '-'}</p>
            <p>运行时长：{health?.uptime ?? '-'}</p>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
