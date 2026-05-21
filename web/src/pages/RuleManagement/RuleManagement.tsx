import { DeleteOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons';
import { Button, Input, message, Popconfirm, Space, Table, Tabs, Tag, Upload } from 'antd';
import type { UploadProps } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { rulesApi } from '@/services';
import type { RuleSearchMatch, RuleVersionDetail, RuleVersionSummary } from '@/types/rule';
import { formatDateTime } from '@/utils/format';

export function RuleManagement() {
  const [versions, setVersions] = useState<RuleVersionSummary[]>([]);
  const [detail, setDetail] = useState<RuleVersionDetail | null>(null);
  const [matches, setMatches] = useState<RuleSearchMatch[]>([]);

  const load = useCallback(async () => {
    const response = await rulesApi.versions();
    setVersions(response.data.items);
    if (!detail) {
      const active = response.data.items.find((item) => item.isActive) ?? response.data.items[0];
      if (active) {
        const detailResponse = await rulesApi.detail(active.versionId);
        setDetail(detailResponse.data);
      }
    }
  }, [detail]);

  useEffect(() => {
    void load();
  }, [load]);

  const uploadProps: UploadProps = {
    showUploadList: false,
    customRequest: async ({ file, onSuccess }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('versionName', '新导入规则');
      await rulesApi.importRules(formData);
      message.success('规则文件已上传');
      onSuccess?.({});
      void load();
    },
  };

  const openDetail = async (versionId: string) => {
    const response = await rulesApi.detail(versionId);
    setDetail(response.data);
  };

  const searchRule = async (code: string) => {
    if (!code.trim()) return;
    const response = await rulesApi.search(code);
    setMatches(response.data.matches);
  };

  return (
    <div>
      <PageHeader
        title="规则管理"
        description="管理 DRG 规则版本，查看 MDC、ADRG、DRG 与 MCC/CC 规则。"
        extra={
          <Upload {...uploadProps}>
            <Button type="primary" icon={<UploadOutlined />}>
              导入规则
            </Button>
          </Upload>
        }
      />
      <div className="content-band">
        <Space style={{ marginBottom: 16 }}>
          <Input.Search placeholder="按编码搜索规则" allowClear onSearch={(value) => void searchRule(value)} />
          {matches.map((match) => (
            <Tag key={`${match.ruleType}-${match.code}`} color="blue">
              {match.code} {match.name}
            </Tag>
          ))}
        </Space>
        <Table
          rowKey="versionId"
          dataSource={versions}
          pagination={false}
          columns={[
            { title: '版本', dataIndex: 'versionName' },
            {
              title: '状态',
              dataIndex: 'status',
              width: 120,
              render: (_, record) => <Tag color={record.isActive ? 'green' : 'default'}>{record.isActive ? '活跃' : record.status}</Tag>,
            },
            {
              title: '规则数量',
              dataIndex: 'ruleCount',
              render: (count) => `MDC:${count.mdc} ADRG:${count.adrg} DRG:${count.drg}`,
            },
            { title: '导入时间', dataIndex: 'importedAt', render: formatDateTime },
            {
              title: '操作',
              width: 260,
              render: (_, record) => (
                <Space>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => void openDetail(record.versionId)}>
                    查看
                  </Button>
                  {!record.isActive ? (
                    <Button
                      size="small"
                      onClick={async () => {
                        await rulesApi.activate(record.versionId);
                        message.success('规则版本已激活');
                        void load();
                      }}
                    >
                      激活
                    </Button>
                  ) : null}
                  {!record.isActive ? (
                    <Popconfirm title="删除非活跃规则版本？" onConfirm={() => void rulesApi.remove(record.versionId)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  ) : null}
                </Space>
              ),
            },
          ]}
        />
      </div>
      {detail ? (
        <div className="content-band" style={{ marginTop: 20 }}>
          <Tabs
            items={[
              {
                key: 'mdc',
                label: `MDC (${detail.mdcList.length})`,
                children: <RuleTable data={detail.mdcList} columns={['code', 'name']} />,
              },
              {
                key: 'adrg',
                label: `ADRG (${detail.adrgList.length})`,
                children: <RuleTable data={detail.adrgList} columns={['code', 'name', 'mdc']} />,
              },
              {
                key: 'drg',
                label: `DRG (${detail.drgList.length})`,
                children: <RuleTable data={detail.drgList} columns={['code', 'name', 'adrg', 'ccLevel']} />,
              },
              {
                key: 'mcc',
                label: `MCC (${detail.mccList.length})`,
                children: <RuleTable data={detail.mccList} columns={['code', 'name', 'level']} />,
              },
              {
                key: 'cc',
                label: `CC (${detail.ccList.length})`,
                children: <RuleTable data={detail.ccList} columns={['code', 'name', 'level']} />,
              },
            ]}
          />
        </div>
      ) : null}
    </div>
  );
}

function RuleTable({ data, columns }: { data: object[]; columns: string[] }) {
  return (
    <Table
      size="small"
      rowKey={(record) => String((record as { code?: string }).code)}
      dataSource={data}
      pagination={false}
      columns={columns.map((key) => ({ title: key, dataIndex: key }))}
    />
  );
}
