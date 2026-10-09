"use client";
import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { number, type Schema } from "./shared";
export function ScoreRing({
  value,
  label,
  band,
  explanation,
  size = 160,
  hue,
}: {
  value: number | null;
  label: string;
  band?: Schema["Band"];
  explanation?: ReactNode;
  size?: number;
  /** A fixed accent for rings that are not a readiness band, such as coverage. */
  hue?: "citron" | "sage" | "teal" | "ochre" | "clay" | "plum";
}) {
  const reduced = useReducedMotion();
  const compact = size < 120;
  const valid =
    value !== null && Number.isFinite(value) && value >= 0 && value <= 100;
  const circumference = 2 * Math.PI * 58;
  const bandHue = band === "ready" ? "sage" : band === "developing" ? "ochre" : band === "not_ready" ? "clay" : "citron";
  const color = `var(--hue-${hue ?? bandHue})`;
  const textColor = `var(--hue-${hue ?? bandHue}-text)`;
  return (
    <div
      data-component="ScoreRing"
      className="flex min-w-0 flex-col items-center gap-2"
    >
      <div
        className="relative max-w-full"
        style={{ width: size, aspectRatio: "1" }}
        role="img"
        aria-label={`${label}: ${valid ? number(value!) + " out of 100" : "unavailable"}${band ? `, ${band.replaceAll("_", " ")}` : ""}`}
      >
        <svg
          viewBox="0 0 144 144"
          aria-hidden="true"
          className="h-full w-full -rotate-90"
        >
          <circle
            cx="72"
            cy="72"
            r="58"
            fill="none"
            stroke="color-mix(in srgb, var(--text) 13%, transparent)"
            strokeWidth="7"
          />
          <motion.circle
            cx="72"
            cy="72"
            r="58"
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            // Match server/client markup; reduced motion settles instantly after hydration.
            initial={{ strokeDasharray: `0 ${circumference}` }}
            animate={{
              strokeDasharray: `${circumference * (valid ? value! / 100 : 0)} ${circumference}`,
            }}
            transition={{ duration: reduced ? 0 : 0.4, ease: "easeOut" }}
          />
        </svg>
        <div
          aria-hidden="true"
          className={`absolute inset-0 flex flex-col items-center justify-center gap-1 text-center ${compact ? "px-3" : "px-7"}`}
        >
          <span
            style={{ color: textColor }}
            className={`${compact ? "text-xl" : "text-4xl"} font-semibold tracking-tight tabular-nums`}
          >
            {valid ? number(value!) : "—"}
          </span>
          {!compact && (
            <span className="text-xs font-medium text-muted-readable">
              {label}
            </span>
          )}
        </div>
      </div>
      {compact && (
        <span
          aria-hidden="true"
          className="max-w-full break-anywhere text-center text-xs font-medium text-muted-readable"
        >
          {label}
        </span>
      )}
      {explanation}
    </div>
  );
}
