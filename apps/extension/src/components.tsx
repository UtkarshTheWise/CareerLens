import { useEffect, useState, type ReactNode } from "react";
import type { components } from "@careerlens/api-client";
export function Card({ children }: { children: ReactNode }) {
  return <section className="card">{children}</section>;
}
export function Ring({
  value,
  label,
  why,
}: {
  value: number;
  label: string;
  why: string;
}) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(frame);
  }, []);
  const valid = Number.isFinite(value) && value >= 0 && value <= 100,
    c = 2 * Math.PI * 48;
  return (
    <div className="match-ring">
      <div
        role="img"
        aria-label={
          label + ": " + (valid ? value + " out of 100" : "unavailable")
        }
        className="ring-picture"
      >
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle
            cx="60"
            cy="60"
            r="48"
            fill="none"
            stroke="var(--surface-2)"
            strokeWidth="12"
          />
          <circle
            className="ring-arc"
            cx="60"
            cy="60"
            r="48"
            fill="none"
            stroke="var(--primary)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={ready && valid ? c * (1 - value / 100) : c}
          />
        </svg>
        <strong aria-hidden="true">
          {valid
            ? new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(
                value,
              )
            : "—"}
        </strong>
      </div>
      <span>{label}</span>
      <details>
        <summary>Why?</summary>
        <p className="muted">{why}</p>
      </details>
    </div>
  );
}
const levels = {
  strong: "Strong",
  moderate: "Moderate",
  weak: "Weak",
  unverified: "Unverified",
  missing: "Missing",
};
export function LevelPill({
  level,
}: {
  level: components["schemas"]["EvidenceLevel"];
}) {
  return <span className={"pill level-" + level}>{levels[level]}</span>;
}
export function Status({
  children,
  error = false,
}: {
  children: ReactNode;
  error?: boolean;
}) {
  return (
    <p role={error ? "alert" : "status"} className={error ? "error" : "muted"}>
      {children}
    </p>
  );
}
