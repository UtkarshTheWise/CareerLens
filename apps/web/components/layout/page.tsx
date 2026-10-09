"use client";
import Link from "next/link";
import * as React from "react";
import { cn } from "@/lib/utils";

/* Shared screen structure: the homepage's eyebrow, large light headings, hairline sections and flat panels. */

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-x-8 gap-y-4 pb-8", className)}>
      <div className="min-w-0">
        {eyebrow ? <p className="eyebrow mb-3">{eyebrow}</p> : null}
        <h1 className="page-title">{title}</h1>
        {description ? <p className="lede mt-3">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </header>
  );
}

export function Section({
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
  id,
}: {
  eyebrow?: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  id?: string;
}) {
  const titleId = React.useId();
  return (
    <section id={id} aria-labelledby={title ? titleId : undefined} className={cn("app-section", className)}>
      {title ? (
        <div className="mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
          <div className="min-w-0">
            {eyebrow ? <p className="eyebrow mb-2">{eyebrow}</p> : null}
            <h2 id={titleId} className="section-title">{title}</h2>
            {description ? <p className="lede mt-2">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Panel({
  label,
  title,
  actions,
  footer,
  children,
  className,
  as: Tag = "div",
}: {
  label?: string;
  title?: React.ReactNode;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "aside";
}) {
  return (
    <Tag className={cn("panel", className)}>
      {label ? <span className="panel-label">{label}</span> : null}
      {title || actions ? (
        <div className="panel-header">
          {title ? <h3 className="text-[17px] font-medium tracking-[-.02em]">{title}</h3> : <span />}
          {actions}
        </div>
      ) : null}
      {children}
      {footer ? <div className="panel-footer">{footer}</div> : null}
    </Tag>
  );
}

export type Tone = "success" | "warning" | "danger" | "muted" | "primary";

/** Coloured text with a dot. Always renders its label, so colour is never the only signal. */
export function StatusText({ tone, children, className }: { tone: Tone; children: React.ReactNode; className?: string }) {
  return <span className={cn("status-text", `tone-text-${tone}`, className)}>{children}</span>;
}

export function Metric({
  value,
  unit,
  label,
  className,
}: {
  value: React.ReactNode;
  unit?: string;
  label?: string;
  className?: string;
}) {
  return (
    <span className={cn("metric", className)} aria-label={label}>
      <span>{value}</span>
      {unit ? <span className="metric-unit">{unit}</span> : null}
    </span>
  );
}

export function TextLink({
  href,
  external,
  children,
  className,
}: {
  href: string;
  external?: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cn("text-link", className)}>
        {children} ↗<span className="sr-only"> (opens in a new tab)</span>
      </a>
    );
  }
  return <Link href={href} className={cn("text-link", className)}>{children}</Link>;
}

/** A hairline row that opens and closes a region, like the homepage roadmap and FAQ. */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  className,
}: {
  summary: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const id = React.useId();
  return (
    <div className={className}>
      <button type="button" className="disclosure-row" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        <span>{summary}</span>
      </button>
      <div id={id} hidden={!open} className="pb-4">{children}</div>
    </div>
  );
}

export type SelectRowItem = {
  id: string;
  title: React.ReactNode;
  secondary?: React.ReactNode;
  status?: React.ReactNode;
};

/** Selectable rows with one explanation below, announced politely. The homepage's skill list, reusable. */
export function SelectRowGroup({
  label,
  items,
  selectedId,
  onSelect,
  detail,
  multiple = false,
  selectedIds,
  className,
}: {
  label: string;
  items: SelectRowItem[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
  detail?: React.ReactNode;
  multiple?: boolean;
  selectedIds?: string[];
  className?: string;
}) {
  const isOn = (id: string) => (multiple ? !!selectedIds?.includes(id) : selectedId === id);
  return (
    <div className={className}>
      <div role="group" aria-label={label} className="hairline-list">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={cn("select-row", !item.secondary && "select-row-plain")}
            aria-pressed={isOn(item.id)}
            onClick={() => onSelect(item.id)}
          >
            <span className="min-w-0 break-anywhere font-medium">{item.title}</span>
            {item.secondary ? <span className="min-w-0 break-anywhere text-muted-readable">{item.secondary}</span> : null}
            {item.status ?? <span />}
          </button>
        ))}
      </div>
      {detail !== undefined ? (
        <div aria-live="polite" className="mt-4">
          {detail ? <div key={String(selectedId)} className="inset-note detail-enter">{detail}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
