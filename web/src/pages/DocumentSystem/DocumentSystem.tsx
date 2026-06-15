import {
  DeleteOutlined,
  DownloadOutlined,
  FileTextOutlined,
  PlusOutlined,
  SendOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { Button, Dropdown, Empty, Input, Select, Space, Spin, Tag, Tooltip, message } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MarkdownPreview } from '@/components/Common/MarkdownPreview';
import { documentsApi } from '@/services';
import type {
  DocType,
  DocumentConversationSummary,
  DocumentDetail,
  DocumentMessage,
} from '@/types/document';
import { triggerDownload } from '@/utils/download';
import { docTypeLabels } from '@/utils/constants';

const docTypeOptions: { value: DocType; label: string }[] = (
  ['requirements', 'design', 'testing', 'management', 'configuration', 'general'] as DocType[]
).map((value) => ({ value, label: docTypeLabels[value] }));

const quickPrompts = [
  '帮我起草一份 DRG-Agent 的需求分析文档',
  '生成一份概要设计文档，体现前后端分离与智能体编排',
  '写一份 DRG 入组的测试文档，区分正常/边界/异常用例',
];

export function DocumentSystem() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<DocumentConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DocumentMessage[]>([]);
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [input, setInput] = useState('');
  const [docType, setDocType] = useState<DocType | undefined>('requirements');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadConversations = async () => {
    const response = await documentsApi.listConversations({ page: 1, pageSize: 50 });
    setConversations(response.data.items);
  };

  useEffect(() => {
    void loadConversations();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const selectConversation = async (convId: string) => {
    setActiveId(convId);
    const response = await documentsApi.conversation(convId);
    setMessages(response.data.messages);
    setDoc(response.data.document);
    setDocType((response.data.docType as DocType) ?? 'general');
  };

  const startNew = () => {
    setActiveId(null);
    setMessages([]);
    setDoc(null);
    setInput('');
    setDocType('requirements');
  };

  const send = async (text?: string) => {
    const instruction = (text ?? input).trim();
    if (!instruction || sending) return;
    setSending(true);
    // 乐观追加用户气泡
    const optimistic: DocumentMessage = {
      messageId: `tmp-${Date.now()}`,
      role: 'user',
      content: instruction,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setInput('');
    try {
      let convId = activeId;
      if (!convId) {
        const created = await documentsApi.createConversation({ docType });
        convId = created.data.conversationId;
        setActiveId(convId);
      }
      const response = await documentsApi.sendMessage(convId, instruction);
      setMessages((prev) => [...prev, response.data.assistantMessage]);
      setDoc(response.data.document);
      await loadConversations();
    } catch {
      message.error('生成失败，请稍后重试');
      setMessages((prev) => prev.filter((item) => item.messageId !== optimistic.messageId));
      setInput(instruction);
    } finally {
      setSending(false);
    }
  };

  const removeConversation = async (convId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    await documentsApi.removeConversation(convId);
    if (convId === activeId) startNew();
    await loadConversations();
    message.success('会话已删除');
  };

  const submitDoc = async () => {
    if (!doc) return;
    await documentsApi.submit(doc.docId);
    message.success('文档已提交至虚拟文档系统');
    if (activeId) await selectConversation(activeId);
  };

  return (
    <div className="doc-chat">
      {/* 会话列表 */}
      <aside className="doc-chat__sidebar">
        <Button type="primary" icon={<PlusOutlined />} block onClick={startNew}>
          新建文档对话
        </Button>
        <Button
          type="text"
          icon={<UnorderedListOutlined />}
          block
          style={{ marginTop: 8, justifyContent: 'flex-start' }}
          onClick={() => navigate('/docs/all')}
        >
          全部文档
        </Button>
        <div className="doc-chat__conv-list">
          {conversations.length === 0 && (
            <p className="doc-chat__hint">还没有对话，点击上方开始。</p>
          )}
          {conversations.map((conv) => (
            <button
              type="button"
              key={conv.conversationId}
              className={`doc-chat__conv${conv.conversationId === activeId ? ' is-active' : ''}`}
              onClick={() => void selectConversation(conv.conversationId)}
            >
              <FileTextOutlined />
              <span className="doc-chat__conv-title">{conv.title}</span>
              <Tooltip title="删除会话">
                <DeleteOutlined
                  className="doc-chat__conv-del"
                  onClick={(event) => void removeConversation(conv.conversationId, event)}
                />
              </Tooltip>
            </button>
          ))}
        </div>
      </aside>

      {/* 对话区 */}
      <section className="doc-chat__main">
        <div className="doc-chat__messages" ref={scrollRef}>
          {messages.length === 0 && !sending && (
            <div className="doc-chat__welcome">
              <h2>虚拟文档系统 · 对话式生成</h2>
              <p>用自然语言告诉我你需要的工程文档，我会生成并支持多轮迭代修订。</p>
              <Space direction="vertical" style={{ width: '100%', maxWidth: 520 }}>
                {quickPrompts.map((prompt) => (
                  <button
                    type="button"
                    key={prompt}
                    className="doc-chat__quick"
                    onClick={() => void send(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </Space>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.messageId} className={`doc-chat__bubble doc-chat__bubble--${msg.role}`}>
              {msg.content}
              {msg.docVersion && <span className="doc-chat__ver">{msg.docVersion}</span>}
            </div>
          ))}
          {sending && (
            <div className="doc-chat__bubble doc-chat__bubble--assistant">
              <Spin size="small" /> <span style={{ marginLeft: 8 }}>正在生成文档…</span>
            </div>
          )}
        </div>

        <div className="doc-chat__composer">
          {!activeId && (
            <Select
              size="small"
              value={docType}
              onChange={setDocType}
              options={docTypeOptions}
              style={{ width: 130, marginBottom: 8 }}
              placeholder="文档类型(可选)"
              allowClear
            />
          )}
          <div className="doc-chat__composer-row">
            <Input.TextArea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="描述你想要的文档，或对当前文档提出修改意见…（Enter 发送，Shift+Enter 换行）"
              autoSize={{ minRows: 1, maxRows: 6 }}
              onPressEnter={(event) => {
                if (!event.shiftKey) {
                  event.preventDefault();
                  void send();
                }
              }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={sending}
              onClick={() => void send()}
            >
              发送
            </Button>
          </div>
        </div>
      </section>

      {/* 文档预览 */}
      <aside className="doc-chat__preview">
        {doc ? (
          <>
            <div className="doc-chat__preview-head">
              <div>
                <h3>{doc.title}</h3>
                <Space size={4} wrap>
                  <Tag color="green">{docTypeLabels[doc.type] ?? doc.type}</Tag>
                  <Tag>{doc.version}</Tag>
                </Space>
              </div>
              <Space>
                <Dropdown
                  trigger={['click']}
                  menu={{
                    items: [
                      { key: 'markdown', label: 'Markdown' },
                      { key: 'html', label: 'HTML' },
                      { key: 'pdf', label: 'PDF' },
                    ],
                    onClick: ({ key }) => {
                      triggerDownload(`/documents/${doc.docId}/download?format=${key}`);
                      message.success(`${key.toUpperCase()} 下载已开始`);
                    },
                  }}
                >
                  <Button size="small" icon={<DownloadOutlined />}>
                    下载
                  </Button>
                </Dropdown>
                <Button size="small" onClick={() => navigate(`/docs/detail/${doc.docId}`)}>
                  详情/版本
                </Button>
                <Button size="small" type="primary" onClick={() => void submitDoc()}>
                  提交
                </Button>
              </Space>
            </div>
            <div className="doc-chat__preview-body markdown-preview">
              <MarkdownPreview content={doc.content} />
            </div>
          </>
        ) : (
          <Empty
            style={{ marginTop: 80 }}
            description="文档预览将在这里实时显示"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </aside>
    </div>
  );
}
