import { EyeOutlined, FileAddOutlined } from '@ant-design/icons';
import { Button, Input, Select, Space, Table, Tag } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader } from '@/components/Common/PageHeader';
import { useDebounce } from '@/hooks/useDebounce';
import { useDocumentStore } from '@/stores/documentStore';
import type { DocType, DocumentStatus } from '@/types/document';
import { docStatusLabels, docTypeLabels } from '@/utils/constants';
import { fileSizeText, formatDateTime } from '@/utils/format';

export function DocumentList() {
  const navigate = useNavigate();
  const { type } = useParams();
  const [keyword, setKeyword] = useState('');
  const debouncedKeyword = useDebounce(keyword);
  const { documents, filter, setFilter, fetchDocuments } = useDocumentStore();

  useEffect(() => {
    setFilter({ type: type as DocType, keyword: debouncedKeyword || undefined });
  }, [debouncedKeyword, setFilter, type]);

  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments, filter]);

  return (
    <div>
      <PageHeader
        title={`${docTypeLabels[(type as DocType) || 'requirements'] ?? '文档'}列表`}
        extra={
          <Button type="primary" icon={<FileAddOutlined />} onClick={() => navigate('/docs')}>
            生成文档
          </Button>
        }
      />
      <div className="content-band">
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            allowClear
            placeholder="全部状态"
            style={{ width: 150 }}
            onChange={(status?: DocumentStatus) => setFilter({ status })}
            options={Object.entries(docStatusLabels).map(([value, label]) => ({ value, label }))}
          />
          <Input.Search placeholder="搜索文档标题" allowClear value={keyword} onChange={(event) => setKeyword(event.target.value)} />
        </Space>
        <Table
          rowKey="docId"
          dataSource={documents}
          pagination={false}
          columns={[
            { title: '文档标题', dataIndex: 'title' },
            { title: '类型', dataIndex: 'type', render: (value: DocType) => docTypeLabels[value] },
            { title: '状态', dataIndex: 'status', render: (value: DocumentStatus) => <Tag>{docStatusLabels[value]}</Tag> },
            { title: '版本', dataIndex: 'version' },
            { title: '创建时间', dataIndex: 'createdAt', render: formatDateTime },
            { title: '大小', dataIndex: 'fileSize', render: fileSizeText },
            {
              title: '操作',
              width: 120,
              render: (_, record) => (
                <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/docs/detail/${record.docId}`)}>
                  查看
                </Button>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
}
