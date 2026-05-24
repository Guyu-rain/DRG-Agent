import type { ReactNode } from 'react';
import { routeItems } from '@/utils/constants';
import './PageHeader.css';

interface PageHeaderProps {
  title: string;
  /** Short paragraph below the title — set in italic small caps style. */
  description?: string;
  /** Optional override for the eyebrow numeral (e.g., "00 · 概览"). Defaults to derived nav index. */
  eyebrow?: string;
  /** Right-side slot for filters / actions. */
  extra?: ReactNode;
}

function deriveEyebrow(pathname: string): string {
  const matchIdx = routeItems.findIndex((r) => {
    if (r.key === '/') return pathname === '/';
    return pathname.startsWith(r.key);
  });
  const idx = matchIdx === -1 ? 0 : matchIdx;
  const item = routeItems[idx];
  return `№ ${String(idx + 1).padStart(2, '0')} · ${item.label}`;
}

// Read pathname from window.location to stay safe outside a Router context
// (used in component-level vitest renders).
function currentPath(): string {
  if (typeof window === 'undefined') return '/';
  return window.location?.pathname ?? '/';
}

export function PageHeader({ title, description, eyebrow, extra }: PageHeaderProps) {
  const eyebrowText = eyebrow ?? deriveEyebrow(currentPath());

  return (
    <header className="page-head">
      <div className="page-head__inner">
        <div className="page-head__text">
          <span className="page-head__eyebrow">{eyebrowText}</span>
          <h1 className="page-head__title">{title}</h1>
          {description ? <p className="page-head__sub">{description}</p> : null}
        </div>
        {extra ? <div className="page-head__extra">{extra}</div> : null}
      </div>
      <div className="page-head__rule" aria-hidden="true">
        <span className="page-head__rule-tick" />
      </div>
    </header>
  );
}
