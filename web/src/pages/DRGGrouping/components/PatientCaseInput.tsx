import { Tabs } from 'antd';
import type { StructuredCaseInput } from '@/types/case';
import { StructuredFormInput } from './StructuredFormInput';
import { TextModeInput } from './TextModeInput';

interface PatientCaseInputProps {
  mode: 'text' | 'structured';
  text: string;
  structured: StructuredCaseInput;
  onModeChange: (mode: 'text' | 'structured') => void;
  onTextChange: (value: string) => void;
  onStructuredChange: (value: StructuredCaseInput) => void;
}

export function PatientCaseInput({
  mode,
  text,
  structured,
  onModeChange,
  onTextChange,
  onStructuredChange,
}: PatientCaseInputProps) {
  return (
    <Tabs
      activeKey={mode}
      onChange={(key) => onModeChange(key as 'text' | 'structured')}
      items={[
        { key: 'text', label: '文本模式', children: <TextModeInput value={text} onChange={onTextChange} /> },
        {
          key: 'structured',
          label: '结构化模式',
          children: <StructuredFormInput value={structured} onChange={onStructuredChange} />,
        },
      ]}
    />
  );
}
