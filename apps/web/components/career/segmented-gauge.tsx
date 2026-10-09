import { number } from "./shared";
export type GaugeSegment = { label: string; value: number };
/** One hue per score component, in order. report-overview uses the same list for its rows. */
export const GAUGE_HUES = ["citron", "sage", "teal", "ochre", "clay", "plum"] as const;
const colors = GAUGE_HUES.map((hue) => `var(--hue-${hue})`);
export function SegmentedGauge({
  segments,
  label,
}: {
  segments: GaugeSegment[];
  label: string;
}) {
  const total = segments.reduce(
    (sum, segment) => sum + Math.max(0, segment.value),
    0,
  );
  const circumference = 2 * Math.PI * 58;
  let offset = 0;
  return (
    <div
      data-component="SegmentedGauge"
      className="flex min-w-0 flex-col items-center gap-5"
    >
      <svg
        viewBox="0 0 144 144"
        className="w-44 max-w-full -rotate-90"
        role="img"
        aria-label={`${label}: ${segments.map((s) => `${s.label} ${number(s.value)}%`).join(", ")}`}
      >
        <title>{label}</title>
        <circle
          cx="72"
          cy="72"
          r="58"
          fill="none"
          stroke="color-mix(in srgb, var(--text) 13%, transparent)"
          strokeWidth="7"
        />
        {total > 0 &&
          segments.map((segment, index) => {
            const length = (Math.max(0, segment.value) / total) * circumference;
            const start = offset;
            offset += length;
            return (
              <circle
                key={segment.label}
                cx="72"
                cy="72"
                r="58"
                fill="none"
                stroke={colors[index % colors.length]}
                strokeWidth="7"
                strokeDasharray={`${Math.max(0, length - 3)} ${circumference}`}
                strokeDashoffset={-start}
              />
            );
          })}
      </svg>
      {total === 0 ? (
        <p className="text-sm text-muted-readable">No breakdown available.</p>
      ) : (
        <ul className="w-full space-y-3">
          {segments.map((segment, index) => (
            <li key={segment.label} className="flex items-center gap-2 text-xs">
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ background: colors[index % colors.length] }}
                aria-hidden="true"
              />
              <span className="flex-1">{segment.label}</span>
              <span className="font-medium tabular-nums">
                {number(segment.value)}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
