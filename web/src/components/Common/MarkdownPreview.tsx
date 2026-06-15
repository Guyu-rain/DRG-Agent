import { Table, Typography } from 'antd';

/** 轻量 Markdown 预览: 支持标题、列表、表格、段落。供文档详情与对话工作台共用。 */
export function MarkdownPreview({ content }: { content: string }) {
  const lines = content.split('\n');
  const nodes: React.ReactNode[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const next = lines[index + 1];
    if (line.includes('|') && next && /^\s*\|?[\s:-]+\|/.test(next)) {
      const headers = line.split('|').map((cell) => cell.trim()).filter(Boolean);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].includes('|')) {
        rows.push(lines[index].split('|').map((cell) => cell.trim()).filter(Boolean));
        index += 1;
      }
      index -= 1;
      nodes.push(
        <Table
          key={`table-${index}`}
          size="small"
          pagination={false}
          dataSource={rows.map((row, rowIndex) => ({ key: rowIndex, row }))}
          columns={headers.map((header, columnIndex) => ({
            title: header,
            render: (_: unknown, record: { row: string[] }) => record.row[columnIndex] ?? '',
          }))}
        />,
      );
    } else if (line.startsWith('# ')) {
      nodes.push(<Typography.Title key={index}>{line.slice(2)}</Typography.Title>);
    } else if (line.startsWith('## ')) {
      nodes.push(<Typography.Title level={3} key={index}>{line.slice(3)}</Typography.Title>);
    } else if (line.startsWith('### ')) {
      nodes.push(<Typography.Title level={4} key={index}>{line.slice(4)}</Typography.Title>);
    } else if (line.startsWith('- ')) {
      nodes.push(<Typography.Paragraph key={index}>• {line.slice(2)}</Typography.Paragraph>);
    } else {
      nodes.push(line ? <Typography.Paragraph key={index}>{line}</Typography.Paragraph> : <br key={index} />);
    }
  }
  return <>{nodes}</>;
}
