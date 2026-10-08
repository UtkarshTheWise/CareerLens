"use client";
import Link from "next/link";
import { useEffect } from "react";
import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { ArrowRight, FileSearch, GitBranch, Route, ScanLine, ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const ease = [0.22, 1, 0.36, 1] as const;
const RADIUS = 78;
const CIRC = 2 * Math.PI * RADIUS;

function rise(delay: number, reduce: boolean | null) {
  return reduce
    ? {}
    : { initial: { opacity: 0, y: 24 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.8, delay, ease } };
}

/** An example score ring that draws itself and counts up. The numbers are illustrative, not a real student. */
function ExampleCard({ reduce }: { reduce: boolean | null }) {
  const value = useMotionValue(reduce ? 72 : 0);
  const dash = useTransform(value, (v) => CIRC * (1 - v / 100));
  const shown = useTransform(value, (v) => Math.round(v).toString());
  useEffect(() => {
    if (reduce) return;
    const controls = animate(value, 72, { duration: 2.2, delay: 0.7, ease });
    return () => controls.stop();
  }, [reduce, value]);

  const chips = [
    { label: "Python · strong evidence", className: "-top-4 sm:-left-10", delay: 1.2 },
    { label: "Docker · unverified claim", className: "top-28 sm:-right-12", delay: 1.5 },
    { label: "SQL · 3 repositories", className: "-bottom-4 sm:-left-6", delay: 1.8 },
  ];

  return (
    <div className="relative mx-auto w-full max-w-sm">
      <div className="relative rounded-card border border-border bg-surface p-8 shadow-card">
        <p className="text-xs font-medium text-muted-readable">Job Readiness Score · example</p>
        <div className="relative mx-auto mt-4 size-48">
          <svg viewBox="0 0 200 200" className="size-full -rotate-90" aria-hidden="true">
            <circle cx="100" cy="100" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth="14" />
            <motion.circle
              cx="100"
              cy="100"
              r={RADIUS}
              fill="none"
              stroke="var(--primary)"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={CIRC}
              style={{ strokeDashoffset: dash }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span className="text-5xl font-bold tracking-tight">{shown}</motion.span>
            <span className="text-xs text-muted-readable">out of 100</span>
          </div>
        </div>
        <ul className="mt-5 space-y-2 text-sm">
          {["Projects with real commits", "Skills backed by evidence", "A clear next step"].map((line, i) => (
            <motion.li
              key={line}
              className="flex items-center gap-2"
              {...(reduce
                ? {}
                : { initial: { opacity: 0, x: -12 }, animate: { opacity: 1, x: 0 }, transition: { delay: 1 + i * 0.2, duration: 0.6, ease } })}
            >
              <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
              {line}
            </motion.li>
          ))}
        </ul>
      </div>
      {chips.map((chip, i) => (
        <motion.span
          key={chip.label}
          aria-hidden="true"
          className={`absolute ${chip.className} hidden rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium shadow-card sm:block`}
          {...(reduce
            ? {}
            : {
                initial: { opacity: 0, scale: 0.8 },
                animate: { opacity: 1, scale: 1, y: [0, -8, 0] },
                transition: {
                  opacity: { delay: chip.delay, duration: 0.5 },
                  scale: { delay: chip.delay, duration: 0.5, ease },
                  y: { delay: chip.delay, duration: 5 + i, repeat: Infinity, ease: "easeInOut" },
                },
              })}
        >
          {chip.label}
        </motion.span>
      ))}
    </div>
  );
}

const points = [
  { icon: GitBranch, title: "Your work, read", text: "Resume, GitHub and portfolio, checked against what they actually show." },
  { icon: FileSearch, title: "A score you can explain", text: "Every point comes with the reasons behind it." },
  { icon: Route, title: "A clear next step", text: "A short roadmap to close the gaps, with free resources." },
];

export function LandingPage() {
  const reduce = useReducedMotion();
  return (
    <div className="relative min-h-dvh overflow-hidden">
      {!reduce && (
        <>
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute -left-40 -top-40 size-[34rem] rounded-full bg-primary/20 blur-3xl"
            animate={{ x: [0, 60, 0], y: [0, 40, 0] }}
            transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute -right-40 top-1/3 size-[30rem] rounded-full bg-data-2/20 blur-3xl"
            animate={{ x: [0, -50, 0], y: [0, -30, 0] }}
            transition={{ duration: 19, repeat: Infinity, ease: "easeInOut" }}
          />
        </>
      )}
      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
        <Link href="/" className="flex items-center gap-3 text-lg font-bold tracking-tight" aria-label="CareerLens home">
          <span className="flex size-10 items-center justify-center rounded-control bg-primary text-primary-foreground">
            <ScanLine size={24} strokeWidth={1.75} aria-hidden="true" />
          </span>
          CareerLens
        </Link>
        <div className="flex items-center gap-2 sm:gap-4">
          <ThemeToggle />
          <Link href="/login" className="rounded-control px-3 py-2 text-sm font-semibold hover:bg-surface-2">
            Sign in
          </Link>
        </div>
      </header>

      <main id="main-content" className="relative mx-auto max-w-6xl px-5 pb-20 pt-8 sm:px-8 lg:pt-16">
        <div className="grid items-center gap-14 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <motion.p
              {...rise(0, reduce)}
              className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-1.5 text-xs font-medium text-muted-readable"
            >
              <ShieldCheck size={14} aria-hidden="true" /> Evidence over buzzwords
            </motion.p>
            <motion.h1 {...rise(0.1, reduce)} className="text-balance text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
              Show the work <span className="text-primary-text">behind your skills.</span>
            </motion.h1>
            <motion.p {...rise(0.25, reduce)} className="mt-6 max-w-lg text-lg leading-relaxed text-muted-readable">
              CareerLens turns your resume, code and projects into a Job Readiness Score you can explain, and tells you what to build next.
            </motion.p>
            <motion.div {...rise(0.4, reduce)} className="mt-9">
              <Link
                href="/login"
                className="group inline-flex min-h-12 items-center gap-3 rounded-control bg-primary px-7 text-base font-semibold text-primary-foreground shadow-card transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                Get started
                <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
              </Link>
              <p className="mt-3 text-xs text-muted-readable">Free with your Google account.</p>
            </motion.div>
          </div>
          <ExampleCard reduce={reduce} />
        </div>

        <ul className="mt-24 grid gap-5 sm:grid-cols-3">
          {points.map(({ icon: Icon, title, text }, i) => (
            <motion.li
              key={title}
              className="rounded-card border border-border bg-surface p-6 shadow-card"
              {...(reduce
                ? {}
                : { initial: { opacity: 0, y: 28 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, margin: "-60px" }, transition: { duration: 0.7, delay: i * 0.12, ease } })}
            >
              <span className="icon-chip mb-4">
                <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
              </span>
              <h2 className="text-base font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-readable">{text}</p>
            </motion.li>
          ))}
        </ul>
      </main>
    </div>
  );
}
