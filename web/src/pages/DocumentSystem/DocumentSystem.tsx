import { FileAddOutlined, FolderOpenOutlined } from '@ant-design/icons';
import { Button, Card, Col, Form, Input, Modal, Row, Select, Space, Switch, message } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/Common/PageHeader';
import { useDocumentStore } from '@/stores/documentStore';
import type { DocType, DocumentGenerateRequest } from '@/types/document';
import { docTypeLabels } from '@/utils/constants';

const docTypes: DocType[] = ['requirements', 'design', 'testing', 'management', 'configuration'];

export function DocumentSystem() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<DocumentGenerateRequest>();
  const { generateDocument } = useDocumentStore();

  const submit = async () => {
    const values = await form.validateFields();
    const taskId = await generateDocument(values);
    message.success(`文档生成完成：${taskId}`);
    setOpen(false);
  };

  return (
    <div>
      <PageHeader
        title="虚拟文档系统"
        description="按类型管理课程文档，支持智能生成、预览、编辑、提交和版本历史。"
        extra={
          <Button type="primary" icon={<FileAddOutlined />} onClick={() => setOpen(true)}>
            生成文档
          </Button>
        }
      />
      <Row gutter={[16, 16]}>
        {docTypes.map((type) => (
          <Col xs={24} md={12} xl={8} key={type}>
            <Card
              hoverable
              className="doc-type-card"
              onClick={() => navigate(`/docs/type/${type}`)}
              actions={[
                <Space key="open">
                  <FolderOpenOutlined />
                  查看列表
                </Space>,
              ]}
            >
              <Card.Meta
                title={docTypeLabels[type]}
                description={
                  type === 'requirements'
                    ? '需求、用例、分析模型与界面原型'
                    : type === 'design'
                      ? '架构、接口、数据库与类设计'
                      : type === 'testing'
                        ? '测试策略、用例、缺陷与覆盖率'
                        : '过程性文档与配置记录'
                }
              />
            </Card>
          </Col>
        ))}
      </Row>
      <Modal title="生成文档" open={open} footer={null} onCancel={() => setOpen(false)}>
        <Form
          layout="vertical"
          form={form}
          initialValues={{
            docType: 'requirements',
            title: 'DRG-Agent 需求分析文档',
            template: 'srs_template_v1',
            context: {
              includeRequirements: true,
              includeUseCases: true,
              includeAnalysisModel: true,
              includePrototype: false,
              sourceTaskIds: ['TASK-GROUP-20260519-001'],
              ruleVersionId: 'RV-20260519-001',
            },
          }}
          onFinish={() => void submit()}
        >
          <Form.Item label="文档类型" name="docType" rules={[{ required: true }]}>
            <Select options={docTypes.map((type) => ({ value: type, label: docTypeLabels[type] }))} />
          </Form.Item>
          <Form.Item label="文档标题" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="模板" name="template">
            <Input />
          </Form.Item>
          <Space direction="vertical">
            <Form.Item valuePropName="checked" name={['context', 'includeRequirements']} noStyle>
              <Switch checkedChildren="功能需求" unCheckedChildren="功能需求" />
            </Form.Item>
            <Form.Item valuePropName="checked" name={['context', 'includeUseCases']} noStyle>
              <Switch checkedChildren="用例" unCheckedChildren="用例" />
            </Form.Item>
            <Form.Item valuePropName="checked" name={['context', 'includeAnalysisModel']} noStyle>
              <Switch checkedChildren="分析模型" unCheckedChildren="分析模型" />
            </Form.Item>
          </Space>
          <Form.Item style={{ marginTop: 20, marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" aria-label="确认生成文档">
                生成
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
