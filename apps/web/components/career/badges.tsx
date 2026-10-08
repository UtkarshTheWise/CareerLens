import { cn } from "@/lib/utils";
import type { Schema } from "./shared";
const levels: Record<
  Schema["EvidenceLevel"],
  { label: string; style: string }
> = {
  strong: { label: "Strong", style: "tone-success" },
  moderate: { label: "Moderate", style: "tone-primary" },
  weak: { label: "Weak", style: "tone-warning" },
  unverified: { label: "Unverified", style: "tone-muted" },
  missing: { label: "Missing", style: "tone-danger-outline" },
};
const bands: Record<Schema["Band"], { label: string; style: string }> = {
  not_ready: { label: "Not ready", style: "tone-danger-outline" },
  developing: { label: "Developing", style: "tone-warning" },
  ready: { label: "Ready", style: "tone-success" },
};
export function LevelPill({
  level,
  className,
}: {
  level: Schema["EvidenceLevel"];
  className?: string;
}) {
  return (
    <span
      data-component="LevelPill"
      className={cn("status-pill", levels[level].style, className)}
    >
      {levels[level].label}
    </span>
  );
}
export function BandBadge({
  band,
  className,
}: {
  band: Schema["Band"];
  className?: string;
}) {
  return (
    <span
      data-component="BandBadge"
      className={cn("status-pill", bands[band].style, className)}
    >
      {bands[band].label}
    </span>
  );
}
