import { Select } from 'antd';
import { useEffect, useState } from 'react';
import { rulesApi } from '@/services';
import type { RuleVersionSummary } from '@/types/rule';

interface RuleVersionSelectorProps {
  value?: string | null;
  onChange: (value: string) => void;
}

export function RuleVersionSelector({ value, onChange }: RuleVersionSelectorProps) {
  const [versions, setVersions] = useState<RuleVersionSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    rulesApi
      .versions()
      .then((response) => {
        setVersions(response.data.items);
        const active = response.data.items.find((item) => item.isActive);
        if (!value && active) onChange(active.versionId);
      })
      .finally(() => setLoading(false));
  }, [onChange, value]);

  return (
    <Select
      value={value ?? undefined}
      loading={loading}
      placeholder="选择规则版本"
      onChange={onChange}
      options={versions.map((item) => ({
        value: item.versionId,
        label: `${item.versionName}${item.isActive ? '（活跃）' : ''}`,
      }))}
      style={{ width: '100%' }}
    />
  );
}
