import {
  DeleteOutlined,
  DownloadOutlined,
  FileTextOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  SendOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { Button, Dropdown, Empty, Input, Select, Space, Spin, Tag, Tabs, Tooltip, message } from 'antd';
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

const qaQuickPrompts = [
  'DRG 入组引擎的 MDC 匹配逻辑是怎么实现的？',
  'server/app/engine 目录下有哪些文件？各有什么作用？',
  '文档系统的对话式生成与问答模式在代码层面有何区别？',
];

type ChatMode = 'doc_chat' | 'qa';

export function DocumentSystem() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<ChatMode>('doc_chat');
  const [conversations, setConversations] = useState<DocumentConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DocumentMessage[]>([]);
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [input, setInput] = useState('');
  const [docType, setDocType] = useState<DocType | undefined>('requirements');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadConversations = async () => {
    if (mode === 'qa') {
      const response = await documentsApi.listQaConversations();
      setConversations(response.data.items);
    } else {
      const response = await documentsApi.listConversations({ page: 1, pageSize: 50 });
      setConversations(response.data.items);
    }
  };

  useEffect(() => {
    void loadConversations();
  }, [mode]);

  useEffect(() => {
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const selectConversation = async (convId: string) => {
    setActiveId(convId);
    if (mode === 'qa') {
      const response = await documentsApi.qaConversation(convId);
      setMessages(response.data.messages);
      setDoc(null);
    } else {
      const response = await documentsApi.conversation(convId);
      setMessages(response.data.messages);
      setDoc(response.data.document);
      setDocType((response.data.docType as DocType) ?? 'general');
    }
  };

  const startNew = () => {
    setActiveId(null);
    setMessages([]);
    setDoc(null);
    setInput('');
    setDocType('requirements');
  };

  const switchMode = (newMode: string) => {
    setMode(newMode as ChatMode);
    startNew();
  };

  const send = async (text?: string) => {
    const instruction = (text ?? input).trim();
    if (!instruction || sending) return;
    setSending(true);
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
        if (mode === 'qa') {
          const created = await documentsApi.createQaConversation({
            title: instruction.slice(0, 40),
          });
          convId = created.data.conversationId;
        } else {
          const created = await documentsApi.createConversation({ docType });
          convId = created.data.conversationId;
        }
        setActiveId(convId);
      }

      if (mode === 'qa') {
        const response = await documentsApi.sendQaMessage(convId, instruction);
        setMessages((prev) => [...prev, response.data.assistantMessage]);
        setDoc(null);
      } else {
        const response = await documentsApi.sendMessage(convId, instruction);
        setMessages((prev) => [...prev, response.data.assistantMessage]);
        setDoc(response.data.document);
      }
      await loadConversations();
    } catch {
      message.error(mode === 'qa' ? '问答失败，请稍后重试' : '生成失败，请稍后重试');
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

  const isDocMode = mode === 'doc_chat';
  const prompts = isDocMode ? quickPrompts : qaQuickPrompts;
  const welcomeTitle = isDocMode ? '虚拟文档系统 · 对话式生成' : '虚拟文档系统 · 技术问答';
  const welcomeDesc = isDocMode
    ? '用自然语言告诉我你需要的工程文档，我会生成并支持多轮迭代修订。'
    : '向我提出关于 DRG-Agent 项目的技术问题，我会查阅源码后回答。';
  const placeholder = isDocMode
    ? '描述你想要的文档，或对当前文档提出修改意见…（Enter 发送，Shift+Enter 换行）'
    : '输入你的技术问题…（Enter 发送，Shift+Enter 换行）';
  const sendingHint = isDocMode ? '正在生成文档…' : '正在查阅源码并生成回答…';

  return (
    <div className="doc-chat">
      {/* 会话列表 */}
      <aside className="doc-chat__sidebar">
        <Tabs
          activeKey={mode}
          onChange={switchMode}
          style={{ marginBottom: 12 }}
          items={[
            {
              key: 'doc_chat',
              label: (
                <span>
                  <FileTextOutlined /> 文档生成
                </span>
              ),
            },
            {
              key: 'qa',
              label: (
                <span>
                  <QuestionCircleOutlined /> 问答
                </span>
              ),
            },
          ]}
        />
        <Button type="primary" icon={<PlusOutlined />} block onClick={startNew}>
          {isDocMode ? '新建文档对话' : '新建问答'}
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
              {conv.mode === 'qa' ? <QuestionCircleOutlined /> : <FileTextOutlined />}
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
              <h2>{welcomeTitle}</h2>
              <p>{welcomeDesc}</p>
              <Space direction="vertical" style={{ width: '100%', maxWidth: 520 }}>
                {prompts.map((prompt) => (
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
              <MarkdownPreview content={msg.content} />
              {msg.docVersion && <span className="doc-chat__ver">{msg.docVersion}</span>}
            </div>
          ))}
          {sending && (
            <div className="doc-chat__bubble doc-chat__bubble--assistant">
              <Spin size="small" /> <span style={{ marginLeft: 8 }}>{sendingHint}</span>
            </div>
          )}
        </div>

        <div className="doc-chat__composer">
          {!activeId && isDocMode && (
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
              placeholder={placeholder}
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

      {/* 文档预览 (仅文档模式) */}
      {isDocMode && (
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
      )}
    </div>
  );
}
