import type { ReactNode } from 'react';
import './SectionTitle.css';

interface SectionTitleProps {
  /** Optional eyebrow numeral, e.g. "01" — shows above the title in mono caps. */
  eyebrow?: string;
  children: ReactNode;
  /** Right-side slot, e.g. action buttons. */
  extra?: ReactNode;
  className?: string;
}

/**
 * 编辑式段头：左侧鼠尾草细线、可选 eyebrow 序号、衬线段标题，右侧可放操作。
 * 用于替换页面中所有 `<h3 className="section-title">` 的场景，
 * 也兼容直接用 .section-title class 的旧调用点（在 index.css 中定义）。
 */
export function SectionTitle({ eyebrow, children, extra, className }: SectionTitleProps) {
  return (
    <div className={['section-head', className].filter(Boolean).join(' ')}>
      <div className="section-head__text">
        {eyebrow ? <span className="section-head__eyebrow">{eyebrow}</span> : null}
        <h3 className="section-head__title">{children}</h3>
      </div>
      {extra ? <div className="section-head__extra">{extra}</div> : null}
    </div>
  );
}
