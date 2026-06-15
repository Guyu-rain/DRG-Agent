import { DownloadOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons';
import { Button, Descriptions, Drawer, Dropdown, Input, Space, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { MarkdownPreview } from '@/components/Common/MarkdownPreview';
import { PageHeader } from '@/components/Common/PageHeader';
import { documentsApi } from '@/services';
import { useDocumentStore } from '@/stores/documentStore';
import type { DocumentVersion } from '@/types/document';
import { docStatusLabels, docTypeLabels } from '@/utils/constants';
import { triggerDownload } from '@/utils/download';
import { formatDateTime } from '@/utils/format';

export function DocumentDetail() {
  const { id } = useParams();
  const { currentDocument, viewDocument, submitDocument } = useDocumentStore();
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState('');
  const [versions, setVersions] = useState<DocumentVersion[]>([]);

  useEffect(() => {
    if (id) void viewDocument(id);
  }, [id, viewDocument]);

  useEffect(() => {
    setContent(currentDocument?.content ?? '');
  }, [currentDocument]);

  if (!currentDocument) return null;

  const save = async () => {
    const response = await documentsApi.update(currentDocument.docId, { title: currentDocument.title, content });
    setContent(response.data.content);
    message.success('文档已保存');
    setEditing(false);
    await viewDocument(currentDocument.docId);
  };

  const loadVersions = async () => {
    const response = await documentsApi.versions(currentDocument.docId);
    setVersions(response.data.items);
  };

  return (
    <div>
      <PageHeader
        title={currentDocument.title}
        extra={
          <Space wrap>
            <Button icon={<SaveOutlined />} onClick={() => setEditing(true)}>
              编辑
            </Button>
            <Dropdown
              trigger={['click']}
              menu={{
                items: [
                  { key: 'markdown', label: 'Markdown' },
                  { key: 'html', label: 'HTML' },
                  { key: 'pdf', label: 'PDF' },
                ],
                onClick: ({ key }) => {
                  triggerDownload(`/documents/${currentDocument.docId}/download?format=${key}`);
                  message.success(`${key.toUpperCase()} 下载已开始`);
                },
              }}
            >
              <Button icon={<DownloadOutlined />}>下载</Button>
            </Dropdown>
            <Button onClick={() => void loadVersions()}>版本历史</Button>
            <Button type="primary" icon={<SendOutlined />} onClick={() => void submitDocument(currentDocument.docId)}>
              提交
            </Button>
          </Space>
        }
      />
      <div className="content-band">
        <Descriptions column={3} size="small">
          <Descriptions.Item label="类型">{docTypeLabels[currentDocument.type]}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag>{docStatusLabels[currentDocument.status]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="版本">{currentDocument.version}</Descriptions.Item>
          <Descriptions.Item label="生成智能体">{currentDocument.metadata.generatedBy}</Descriptions.Item>
          <Descriptions.Item label="模型">{currentDocument.metadata.modelUsed}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatDateTime(currentDocument.createdAt)}</Descriptions.Item>
        </Descriptions>
      </div>
      <div className="two-column" style={{ marginTop: 20 }}>
        <section className="content-band markdown-preview">
          <MarkdownPreview content={content} />
        </section>
        <aside className="content-band">
          <h3 className="section-title">章节导航</h3>
          <Space direction="vertical">
            {currentDocument.sections.map((section) => (
              <Tag key={section.id}>{section.title} · {section.status}</Tag>
            ))}
          </Space>
          <h3 className="section-title" style={{ marginTop: 20 }}>
            版本历史
          </h3>
          <Space direction="vertical">
            {versions.map((version) => (
              <Typography.Text key={version.version}>
                {version.version} · {version.changeDescription} · {formatDateTime(version.createdAt)}
              </Typography.Text>
            ))}
          </Space>
        </aside>
      </div>
      <Drawer title="编辑文档" open={editing} width={720} onClose={() => setEditing(false)} extra={<Button type="primary" onClick={() => void save()}>保存</Button>}>
        <Input.TextArea rows={22} value={content} onChange={(event) => setContent(event.target.value)} />
      </Drawer>
    </div>
  );
}
