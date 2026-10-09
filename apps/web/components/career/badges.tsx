import { cn } from "@/lib/utils";
import { StatusText, type Tone } from "@/components/layout/page";
import type { Schema } from "./shared";
const levels: Record<
  Schema["EvidenceLevel"],
  { label: string; style: string; tone: Tone }
> = {
  strong: { label: "Strong", style: "tone-success", tone: "success" },
  moderate: { label: "Moderate", style: "tone-primary", tone: "primary" },
  weak: { label: "Weak", style: "tone-warning", tone: "warning" },
  unverified: { label: "Unverified", style: "tone-muted", tone: "muted" },
  missing: { label: "Missing", style: "tone-danger-outline", tone: "danger" },
};
const bands: Record<
  Schema["Band"],
  { label: string; style: string; tone: Tone }
> = {
  not_ready: { label: "Not ready", style: "tone-danger-outline", tone: "danger" },
  developing: { label: "Developing", style: "tone-warning", tone: "warning" },
  ready: { label: "Ready", style: "tone-success", tone: "success" },
};
/** "pill" keeps the filled tag for dense tables; "text" is the homepage's coloured text with a dot. */
export type BadgeVariant = "pill" | "text";
export function LevelPill({
  level,
  className,
  variant = "pill",
}: {
  level: Schema["EvidenceLevel"];
  className?: string;
  variant?: BadgeVariant;
}) {
  if (variant === "text")
    return (
      <StatusText tone={levels[level].tone} className={className}>
        <span data-component="LevelPill">{levels[level].label}</span>
      </StatusText>
    );
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
  variant = "pill",
}: {
  band: Schema["Band"];
  className?: string;
  variant?: BadgeVariant;
}) {
  if (variant === "text")
    return (
      <StatusText tone={bands[band].tone} className={className}>
        <span data-component="BandBadge">{bands[band].label}</span>
      </StatusText>
    );
  return (
    <span
      data-component="BandBadge"
      className={cn("status-pill", bands[band].style, className)}
    >
      {bands[band].label}
    </span>
  );
}
