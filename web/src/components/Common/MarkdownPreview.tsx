import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * 基于 react-markdown + GFM 的 Markdown 渲染器。
 * 同时用于文档预览与对话气泡；所有排版由 index.css 中的 .md-body 规则统一控制，
 * 紧凑（气泡）/宽松（预览）通过父容器附加 .md-compact 区分。
 */
const components: Components = {
  // 外链安全打开
  a: ({ node, ...props }) => {
    void node;
    return <a {...props} target="_blank" rel="noreferrer" />;
  },
  // 表格包一层容器以便横向滚动
  table: ({ node, ...props }) => {
    void node;
    return (
      <div className="md-table-wrap">
        <table {...props} />
      </div>
    );
  },
};

export function MarkdownPreview({ content }: { content: string }) {
  return (
    <div className="md-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content || ''}
      </ReactMarkdown>
    </div>
  );
}
