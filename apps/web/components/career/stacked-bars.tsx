"use client";
import { useReducedMotion } from "framer-motion";
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { CardFrame, CardState, number, type ViewState } from "./shared";
export type StackPoint = {
  label: string;
  first: number;
  second: number;
  third: number;
};
export function StackedBars({
  title,
  description,
  data,
  series,
  state = "ready",
  message,
}: {
  title: string;
  description?: string;
  data: StackPoint[];
  series: [string, string, string];
  state?: ViewState;
  message?: string;
}) {
  const reduced = useReducedMotion();
  return (
    <CardFrame data-component="StackedBars">
      <div>
        <h2>{title}</h2>
        {description && (
          <p className="mt-2 text-xs text-muted-readable">{description}</p>
        )}
      </div>
      <CardState
        state={
          state !== "ready" ? state : data.length === 0 ? "empty" : "ready"
        }
        message={message}
      >
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-readable">
          {series.map((name, index) => (
            <span key={name} className="inline-flex items-center gap-2">
              <span
                className="size-2 rounded-full"
                style={{ background: `var(--data-${index + 1})` }}
                aria-hidden="true"
              />
              {name}
            </span>
          ))}
        </div>
        <div
          className="h-64 min-w-0"
          role="group"
          aria-label={`${title}: ${data.map((p) => `${p.label}, ${series[0]} ${p.first}, ${series[1]} ${p.second}, ${series[2]} ${p.third}`).join("; ")}`}
        >
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart
              data={data}
              margin={{ top: 16, right: 8, left: -25, bottom: 0 }}
              accessibilityLayer
              aria-label={`${title} interactive chart`}
            >
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={50}
              />
              <Tooltip
                cursor={{ fill: "var(--surface-2)" }}
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <div className="rounded-control border border-border bg-surface p-3 text-xs text-text shadow-card">
                      <p className="mb-1 font-semibold">{label}</p>
                      {payload.map((p) => (
                        <p key={String(p.dataKey)}>
                          {p.name}: {number(Number(p.value))}
                        </p>
                      ))}
                    </div>
                  ) : null
                }
              />
              <Bar
                name={series[0]}
                dataKey="first"
                stackId="count"
                fill="var(--data-1)"
                maxBarSize={48}
                isAnimationActive={!reduced}
              />
              <Bar
                name={series[1]}
                dataKey="second"
                stackId="count"
                fill="var(--data-2)"
                maxBarSize={48}
                isAnimationActive={!reduced}
              />
              <Bar
                name={series[2]}
                dataKey="third"
                stackId="count"
                fill="var(--data-3)"
                radius={[6, 6, 0, 0]}
                maxBarSize={48}
                isAnimationActive={!reduced}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <details className="text-xs">
          <summary className="min-h-11 cursor-pointer py-3 text-primary-text">
            View distribution data
          </summary>
          <ul className="space-y-2">
            {data.map((p) => (
              <li key={p.label}>
                {p.label}: {series[0]} {p.first}, {series[1]} {p.second},{" "}
                {series[2]} {p.third}
              </li>
            ))}
          </ul>
        </details>
      </CardState>
    </CardFrame>
  );
}
