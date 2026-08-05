/**
 * Inline SVG icons. No icon dependency, nothing fetched — they inherit
 * `currentColor` and font size, so a stage colour or a muted label carries
 * straight through to the glyph.
 */

type Props = { size?: number; className?: string; title?: string };

function svg(size: number) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none" as const,
    stroke: "currentColor" as const,
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
  };
}

const wrap = (size = 16, className?: string, title?: string) => ({
  ...svg(size),
  className: ["icon-svg", className].filter(Boolean).join(" "),
  ...(title ? { "aria-hidden": undefined, role: "img", "aria-label": title } : {}),
});

export function Sun({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
    </svg>
  );
}

export function Moon({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a7 7 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

export function Board({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <rect x="3" y="4" width="5" height="16" rx="1.5" />
      <rect x="10" y="4" width="5" height="10" rx="1.5" />
      <rect x="17" y="4" width="4" height="13" rx="1.5" />
    </svg>
  );
}

export function Layers({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M12 3 3 7.5l9 4.5 9-4.5L12 3Z" />
      <path d="M3 12.5 12 17l9-4.5" />
      <path d="M3 17 12 21.5 21 17" />
    </svg>
  );
}

export function Gear({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2 2 2 0 1 1-4 0 1.7 1.7 0 0 0-2.9-1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 3 15a2 2 0 1 1 0-4 1.7 1.7 0 0 0 1.4-2.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 10 4a2 2 0 1 1 4 0 1.7 1.7 0 0 0 2.9 1.4l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A1.7 1.7 0 0 0 21 11a2 2 0 1 1 0 4Z" />
    </svg>
  );
}

export function FileText({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" />
      <path d="M14 3v5h5M9 13h6M9 17h4" />
    </svg>
  );
}

export function FileCheck({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" />
      <path d="M14 3v5h5M9 15l2 2 4-4" />
    </svg>
  );
}

export function Send({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M21 3 10.5 13.5M21 3l-6.5 18-4-8.5-8.5-4L21 3Z" />
    </svg>
  );
}

export function Clock({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function Calendar({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <rect x="3.5" y="5" width="17" height="16" rx="2" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
    </svg>
  );
}

export function Flame({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M12 22c3.9 0 6.5-2.5 6.5-6 0-4.5-4-6.5-4.5-11-2 1.5-3 3.5-3 5.5C11 8 9.5 7 9 5.5 7 7.5 5.5 10 5.5 13c0 4 2.9 9 6.5 9Z" />
      <path d="M12 22c1.7 0 2.8-1.2 2.8-2.8 0-2-1.8-2.9-2-4.9-1.2.9-1.8 2.1-1.8 3.2 0 .8-.6 1.2-.9 1.7.3 1.6 1.1 2.8 1.9 2.8Z" />
    </svg>
  );
}

export function Target({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.4" />
    </svg>
  );
}

export function Trophy({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M8 4h8v5a4 4 0 0 1-8 0V4Z" />
      <path d="M8 5.5H5.5A2.5 2.5 0 0 0 8 10M16 5.5h2.5A2.5 2.5 0 0 1 16 10" />
      <path d="M12 13v3M9 20h6M10 20l.5-4M14 20l-.5-4" />
    </svg>
  );
}

export function Sparkles({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M12 3.5l1.6 4.4 4.4 1.6-4.4 1.6L12 15.5l-1.6-4.4L6 9.5l4.4-1.6L12 3.5Z" />
      <path d="M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7.7-1.8Z" />
    </svg>
  );
}

export function Check({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M4.5 12.5l5 5 10-11" />
    </svg>
  );
}

export function Plus({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function Dots({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <circle cx="6" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="18" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function External({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M14 4h6v6M20 4l-8.5 8.5" />
      <path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" />
    </svg>
  );
}

export function Book({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5V5.5Z" />
      <path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5A2.5 2.5 0 0 1 4 20.5Z" />
    </svg>
  );
}

export function Chat({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M20 12a7.5 7.5 0 0 1-10.9 6.7L4 20l1.3-4.1A7.5 7.5 0 1 1 20 12Z" />
      <path d="M9 11h6M9 14h3.5" />
    </svg>
  );
}

export function Lightbulb({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M9 17.5h6M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.5 10.9c.4.3.6.8.6 1.3v.3h5.8v-.3c0-.5.2-1 .6-1.3A6 6 0 0 0 12 3Z" />
    </svg>
  );
}

export function ArrowRight({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="M5 12h13M12.5 5.5 19 12l-6.5 6.5" />
    </svg>
  );
}

export function Star({ size, className, title }: Props) {
  return (
    <svg {...wrap(size, className, title)}>
      <path d="m12 3.8 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8-4.3-4.1 5.9-.9L12 3.8Z" />
    </svg>
  );
}

/** A ring that fills as you approach the weekly target. */
export function ProgressRing({
  value,
  goal,
  size = 62,
}: {
  value: number;
  goal: number;
  size?: number;
}) {
  const r = size / 2 - 5;
  const circumference = 2 * Math.PI * r;
  const done = goal > 0 ? Math.min(1, value / goal) : 0;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="ring"
      role="img"
      aria-label={`${value} of ${goal} applications this week`}
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="var(--line)"
        strokeWidth="5"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={done >= 1 ? "var(--good)" : "var(--accent)"}
        strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - done)}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="central"
        fill="var(--text)"
        fontSize={size * 0.3}
        fontWeight="700"
      >
        {value}
      </text>
    </svg>
  );
}

/** Shown when a job reaches offer. Worth a moment. */
export function Confetti({ className }: { className?: string }) {
  const bits = [
    { x: 8, y: 26, r: -20, c: "var(--stage-offer)" },
    { x: 26, y: 12, r: 15, c: "var(--stage-interview)" },
    { x: 46, y: 22, r: -35, c: "var(--stage-applied)" },
    { x: 66, y: 10, r: 25, c: "var(--stage-screen)" },
    { x: 86, y: 24, r: -15, c: "var(--stage-offer)" },
    { x: 106, y: 14, r: 30, c: "var(--stage-interview)" },
    { x: 17, y: 46, r: 40, c: "var(--stage-applied)" },
    { x: 57, y: 44, r: -25, c: "var(--stage-offer)" },
    { x: 96, y: 46, r: 10, c: "var(--stage-screen)" },
  ];
  return (
    <svg
      width="120"
      height="60"
      viewBox="0 0 120 60"
      className={className}
      aria-hidden
      focusable="false"
    >
      {bits.map((b, i) => (
        <rect
          key={i}
          x={b.x}
          y={b.y}
          width="6"
          height="9"
          rx="1.5"
          fill={b.c}
          transform={`rotate(${b.r} ${b.x + 3} ${b.y + 4.5})`}
        />
      ))}
    </svg>
  );
}
