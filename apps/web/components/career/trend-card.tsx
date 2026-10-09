"use client";
import { useState, useId } from "react";
import { useReducedMotion } from "framer-motion";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceDot,
  ResponsiveContainer,
} from "recharts";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CardFrame, CardState, number, type ViewState } from "./shared";
export type TrendPoint = { label: string; primary: number; secondary?: number };
export type TrendPeriod = "weekly" | "monthly" | "yearly";
const periods = ["weekly", "monthly", "yearly"] as const;
export function TrendCard({
  title,
  description,
  series,
  datasets,
  state = "ready",
  message,
}: {
  title: string;
  description?: string;
  series: [string, string?];
  datasets: Record<TrendPeriod, TrendPoint[]>;
  state?: ViewState;
  message?: string;
}) {
  const [period, setPeriod] = useState<TrendPeriod>("weekly");
  const reduced = useReducedMotion();
  const titleId = useId();
  return (
    <CardFrame data-component="TrendCard">
      <div>
        <h2 id={titleId} className="text-[17px]! font-medium! tracking-[-.02em]!">
          {title}
        </h2>
        {description && (
          <p className="mt-2 text-xs text-muted-readable">{description}</p>
        )}
      </div>
      <Tabs
        value={period}
        onValueChange={(value) => setPeriod(value as TrendPeriod)}
      >
        <TabsList
          variant="line"
          className="h-11! w-full justify-start border-b border-border p-0"
          aria-label={`${title} period`}
        >
          {periods.map((value) => (
            <TabsTrigger
              key={value}
              value={value}
              className="h-11! flex-none rounded-none px-3 text-xs text-muted-readable after:bg-primary! data-[state=active]:text-primary-text active:translate-y-px"
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </TabsTrigger>
          ))}
        </TabsList>
        {periods.map((value) => {
          const data = datasets[value];
          const point = data.at(-1);
          return (
            <TabsContent key={value} value={value} className="mt-4 min-w-0">
              <CardState
                state={
                  state !== "ready"
                    ? state
                    : data.length === 0
                      ? "empty"
                      : "ready"
                }
                message={message}
              >
                <div className="mb-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-readable">
                  {series.map((name, index) => (
                    <span key={name} className="inline-flex items-center gap-2">
                      <span
                        className="h-0.5 w-4"
                        style={{
                          background:
                            index === 0
                              ? "var(--primary)"
                              : "var(--primary-soft)",
                        }}
                        aria-hidden="true"
                      />
                      {name}
                    </span>
                  ))}
                </div>
                <div
                  className="h-64 min-w-0"
                  role="group"
                  aria-label={`${title}, ${value}: ${data.map((p) => `${p.label}, ${series[0]} ${number(p.primary)}${series[1] && p.secondary !== undefined ? `, ${series[1]} ${number(p.secondary)}` : ""}`).join("; ")}`}
                >
                  <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                    <LineChart
                      data={data}
                      margin={{ top: 35, right: 14, left: -25, bottom: 0 }}
                      accessibilityLayer
                      aria-label={`${title} interactive chart`}
                    >
                      <CartesianGrid
                        stroke="var(--chart-grid)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        minTickGap={24}
                      />
                      <YAxis
                        tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        width={50}
                      />
                      <Tooltip
                        defaultIndex={data.length - 1}
                        content={({ active, payload, label }) =>
                          active && payload?.length ? (
                            <div className="rounded-control border border-border bg-surface p-3 text-xs text-text shadow-card">
                              <p className="mb-1 font-semibold">{label}</p>
                              {payload.map((p) => (
                                <p
                                  key={String(p.dataKey)}
                                  className="tabular-nums"
                                >
                                  {p.name}: {number(Number(p.value))}
                                </p>
                              ))}
                            </div>
                          ) : null
                        }
                      />
                      {series[1] && (
                        <Line
                          name={series[1]}
                          type="monotone"
                          dataKey="secondary"
                          stroke="var(--primary-soft)"
                          strokeWidth={2.5}
                          dot={false}
                          isAnimationActive={!reduced}
                        />
                      )}
                      <Line
                        name={series[0]}
                        type="monotone"
                        dataKey="primary"
                        stroke="var(--primary)"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{
                          r: 5,
                          stroke: "var(--surface)",
                          strokeWidth: 3,
                        }}
                        isAnimationActive={!reduced}
                      />
                      {point && (
                        <ReferenceDot
                          x={point.label}
                          y={point.primary}
                          r={5}
                          fill="var(--primary)"
                          stroke="var(--surface)"
                          strokeWidth={3}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <details className="mt-3 text-xs">
                  <summary className="min-h-11 cursor-pointer py-3 text-primary-text">
                    View chart data
                  </summary>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <caption className="sr-only">
                        {title}, {value} data
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col" className="py-2">
                            Period
                          </th>
                          {series.map((s) => (
                            <th scope="col" key={s} className="py-2 text-right">
                              {s}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.map((p) => (
                          <tr key={p.label} className="border-t border-border">
                            <th scope="row" className="py-2 font-normal">
                              {p.label}
                            </th>
                            <td className="text-right tabular-nums">
                              {number(p.primary)}
                            </td>
                            {series[1] && (
                              <td className="text-right tabular-nums">
                                {p.secondary === undefined
                                  ? "—"
                                  : number(p.secondary)}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </CardState>
            </TabsContent>
          );
        })}
      </Tabs>
    </CardFrame>
  );
}
