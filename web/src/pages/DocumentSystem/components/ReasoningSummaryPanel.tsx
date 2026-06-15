import {
  CaretDownOutlined,
  CaretRightOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import { useEffect, useRef, useState } from 'react';
import type { ReasoningStep, ReasoningSummary } from '@/types/document';

interface ReasoningSummaryPanelProps {
  summary: ReasoningSummary;
}

function StepIcon({ step }: { step: ReasoningStep }) {
  if (step.status === 'running') return <LoadingOutlined spin />;
  if (step.status === 'completed') return <CheckCircleOutlined />;
  if (step.status === 'failed') return <CloseCircleOutlined />;
  return <MinusCircleOutlined />;
}

export function ReasoningSummaryPanel({ summary }: ReasoningSummaryPanelProps) {
  const [expanded, setExpanded] = useState(summary.status === 'thinking');
  const userControlled = useRef(false);
  const previousStatus = useRef(summary.status);

  useEffect(() => {
    if (
      previousStatus.current === 'thinking' &&
      summary.status !== 'thinking' &&
      !userControlled.current
    ) {
      setExpanded(false);
    }
    previousStatus.current = summary.status;
  }, [summary.status]);

  const completedCount = summary.steps.filter((step) => step.status === 'completed').length;
  const statusLabel =
    summary.status === 'thinking'
      ? '正在思考'
      : summary.status === 'failed'
        ? '思考过程未完成'
        : `已完成思考 · ${completedCount} 个步骤`;

  const toggle = () => {
    userControlled.current = true;
    setExpanded((value) => !value);
  };

  return (
    <section className={`reasoning-summary reasoning-summary--${summary.status}`}>
      <button
        type="button"
        className="reasoning-summary__toggle"
        aria-expanded={expanded}
        aria-label={expanded ? '收起思考过程' : '展开思考过程'}
        onClick={toggle}
      >
        <span className="reasoning-summary__toggle-icon">
          {expanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
        </span>
        <span>{statusLabel}</span>
        {summary.status === 'thinking' && <LoadingOutlined spin />}
      </button>

      {expanded && (
        <ol className="reasoning-summary__steps">
          {summary.steps.map((step) => (
            <li
              key={step.id}
              className={`reasoning-summary__step reasoning-summary__step--${step.status}`}
            >
              <span className="reasoning-summary__step-icon">
                <StepIcon step={step} />
              </span>
              <span>
                <strong>{step.title}</strong>
                {step.detail && <small>{step.detail}</small>}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
