import { Input } from 'antd';

interface TextModeInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function TextModeInput({ value, onChange }: TextModeInputProps) {
  return (
    <Input.TextArea
      value={value}
      onChange={(event) => onChange(event.target.value)}
      rows={9}
      placeholder="粘贴病历文本，例如：主诊断、次要诊断、主要手术"
    />
  );
}
