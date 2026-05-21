import { PlayCircleOutlined, SaveOutlined } from '@ant-design/icons';
import { Alert, Button, Descriptions, message, Space, Typography } from 'antd';
import { useCallback, useState } from 'react';
import { PageHeader } from '@/components/Common/PageHeader';
import { useGroupingStore } from '@/stores/groupingStore';
import type { StructuredCaseInput } from '@/types/case';
import { demoCaseText } from '@/utils/constants';
import { GroupingResultPanel } from './components/GroupingResultPanel';
import { PatientCaseInput } from './components/PatientCaseInput';
import { RuleVersionSelector } from './components/RuleVersionSelector';
import './DRGGrouping.css';

const defaultStructured: StructuredCaseInput = {
  patientId: 'P001',
  age: 45,
  gender: '男',
  primaryDiagnosis: { code: 'A01.002+G01*', name: '伤寒性脑膜炎' },
  secondaryDiagnoses: [{ code: 'J96.0', name: '急性呼吸衰竭' }],
  primaryProcedure: { code: '38.1000x002', name: '动脉内膜剥脱术', surgeryLevel: 3 },
  otherProcedures: [],
  dischargeType: '医嘱离院',
};

export function DRGGrouping() {
  const [text, setText] = useState(demoCaseText);
  const [structured, setStructured] = useState<StructuredCaseInput>(defaultStructured);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const {
    currentCase,
    currentResult,
    inputMode,
    isExecuting,
    isParsing,
    selectedRuleVersion,
    setInputMode,
    setRuleVersion,
    submitCase,
    parseCase,
    executeGrouping,
    fetchResult,
  } = useGroupingStore();

  const handleExecute = useCallback(async () => {
    try {
      const caseId = await submitCase(
        inputMode === 'text'
          ? { rawText: text, sourceType: 'text' }
          : { structuredData: structured, sourceType: 'structured' },
      );
      await parseCase(caseId);
      const taskId = await executeGrouping();
      setActiveTaskId(taskId);
      await fetchResult(taskId);
      message.success('入组执行完成');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '入组执行失败');
    }
  }, [executeGrouping, fetchResult, inputMode, parseCase, structured, submitCase, text]);

  const resultExpired = currentResult && selectedRuleVersion && activeTaskId && currentResult.taskId !== activeTaskId;

  return (
    <div>
      <PageHeader
        title="DRG 入组工作台"
        description="输入病历、选择规则版本，并查看确定性规则引擎生成的入组结果和证据链。"
      />
      {resultExpired ? <Alert type="warning" showIcon message="规则版本已变化，当前结果可能已过期，请重新入组。" /> : null}
      <div className="two-column">
        <section className="content-band">
          <Space direction="vertical" size={18} style={{ width: '100%' }}>
            <div>
              <Typography.Text strong>规则版本</Typography.Text>
              <RuleVersionSelector value={selectedRuleVersion} onChange={setRuleVersion} />
            </div>
            <PatientCaseInput
              mode={inputMode}
              text={text}
              structured={structured}
              onModeChange={setInputMode}
              onTextChange={setText}
              onStructuredChange={setStructured}
            />
            {currentCase ? (
              <div className="parsed-case-panel muted-panel">
                <h3 className="section-title">解析结果</h3>
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="主诊断">
                    {currentCase.primaryDiagnosis?.code} {currentCase.primaryDiagnosis?.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="次要诊断">
                    {currentCase.secondaryDiagnoses?.map((item) => `${item.code} ${item.name}`).join('；') || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="主要手术">
                    {currentCase.primaryProcedure?.code} {currentCase.primaryProcedure?.name}
                  </Descriptions.Item>
                </Descriptions>
              </div>
            ) : null}
            <div className="drg-input-actions">
              <Button icon={<SaveOutlined />} onClick={() => message.success('样例已保存在当前输入面板')}>
                保存样例
              </Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={isExecuting || isParsing}
                onClick={handleExecute}
              >
                开始入组
              </Button>
            </div>
          </Space>
        </section>
        <section className="content-band">
          <GroupingResultPanel response={currentResult} />
        </section>
      </div>
    </div>
  );
}
