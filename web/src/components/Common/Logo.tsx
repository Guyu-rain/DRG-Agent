interface LogoProps {
  size?: number;
  /** Override stroke / fill color. Defaults to sage. */
  color?: string;
  className?: string;
  title?: string;
}

/**
 * DRG-Agent 品牌徽标 — 抽象的分组树：
 * 顶端单点（MDC）向下分叉为 ADRG（2 点），再分叉为 DRG（4 点）。
 * 用细线 + 圆点构成临床手册式的微图谱。
 */
export function Logo({ size = 28, color = 'var(--sage)', className, title = 'DRG-Agent' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label={title}
    >
      {/* connecting lines */}
      <g stroke={color} strokeWidth="1" strokeLinecap="round">
        <path d="M16 7 L16 12" />
        <path d="M16 12 L10 17 M16 12 L22 17" />
        <path d="M10 17 L6 24 M10 17 L13 24 M22 17 L19 24 M22 17 L26 24" />
      </g>
      {/* nodes */}
      <g fill={color}>
        <circle cx="16" cy="6" r="2" />
        <circle cx="10" cy="17" r="1.6" />
        <circle cx="22" cy="17" r="1.6" />
      </g>
      <g fill="var(--paper)" stroke={color} strokeWidth="1">
        <circle cx="6" cy="25" r="1.3" />
        <circle cx="13" cy="25" r="1.3" />
        <circle cx="19" cy="25" r="1.3" />
        <circle cx="26" cy="25" r="1.3" />
      </g>
    </svg>
  );
}
