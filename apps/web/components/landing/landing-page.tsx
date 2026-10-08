"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Credit } from "@/components/layout/credit";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import styles from "./landing-page.module.css";
const cx = (...names: string[]) => names.map(name => styles[name]).filter(Boolean).join(" ");
const examples = [
  { name: "Python", source: "campus-api", level: "Strong", reason: "Primary language of campus-api, supported by the work in the repository." },
  { name: "Docker", source: "Dockerfile", level: "Strong", reason: "A Dockerfile packages campus-api with its runtime dependencies. The claim has direct repository support." },
  { name: "pytest", source: "Project tests", level: "Moderate", reason: "Tests are present in campus-api. Broader test coverage would strengthen the evidence for this claim." },
];
export function LandingPage() {
  const [selected, setSelected] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [deliverableOpen, setDeliverableOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape" && menuOpen) {
        setMenuOpen(false);
        menuButton.current?.focus();
      }
    };
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !menuButton.current?.closest("header")?.contains(event.target)) setMenuOpen(false);
    };
    window.addEventListener("keydown", close);
    window.addEventListener("pointerdown", closeOutside);
    return () => {
      window.removeEventListener("keydown", close);
      window.removeEventListener("pointerdown", closeOutside);
    };
  }, [menuOpen]);
  useEffect(() => {
    if (!root.current || !window.IntersectionObserver || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const sections = root.current.querySelectorAll("." + styles.reveal);
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.remove(styles["is-waiting"]); observer.unobserve(entry.target); }
    }), { threshold: 0.08 });
    sections.forEach(section => { section.classList.add(styles["is-waiting"]); observer.observe(section); });
    return () => { observer.disconnect(); sections.forEach(section => section.classList.remove(styles["is-waiting"])); };
  }, []);
  return <div ref={root} className={styles.root}>
  <a className={cx("skip-link")} href="#main">Skip to content</a>
  <header className={cx("site-header", "wrap")}>
    <Link className={cx("brand")} href="/" aria-label="CareerLens home"><span className={cx("lens-mark")} aria-hidden="true"></span>CareerLens</Link>
    <nav aria-label="Primary navigation" className={cx("desktop-nav")}>
      <a href="#evidence">The evidence</a><a href="#next-step">Your next step</a><a href="#questions">Questions</a>
    </nav>
    <Link className={cx("header-login")} href="/login">Sign in <span aria-hidden="true">↗</span></Link>
    <ThemeToggle /><button ref={menuButton} className={cx("menu-button")} aria-expanded={menuOpen} aria-controls="mobile-menu" onClick={() => setMenuOpen(!menuOpen)}>Menu</button>
    <nav id="mobile-menu" data-mobile-menu aria-label="Mobile navigation" hidden={!menuOpen} onClick={() => setMenuOpen(false)}>
      <a href="#evidence">The evidence</a><a href="#next-step">Your next step</a><a href="#questions">Questions</a><Link href="/login">Sign in</Link>
    </nav>
  </header>

  <main id="main">
    <section className={cx("hero", "wrap")} aria-labelledby="hero-title">
      <div className={cx("hero-copy")}>
        <p className={cx("eyebrow")}><span className={cx("small-reticle")} aria-hidden="true"></span>For the work you’ve put in</p>
        <h1 id="hero-title">You’ve built it.<br />Now show<br /><span>what it proves.</span></h1>
        <p className={cx("hero-description")}>Your resume makes the claim. Your projects tell the story. Bring them together, see the evidence, and find your next move.</p>
        <div className={cx("hero-actions")}>
          <Link className={cx("button", "primary")} href="/login">Get started <span aria-hidden="true">↗</span></Link>
          <a className={cx("text-link")} href="#evidence">Take a closer look <span aria-hidden="true">↓</span></a>
        </div>
        <p className={cx("input-caption")}>Resume <span aria-hidden="true">/</span> GitHub <span aria-hidden="true">/</span> Portfolio</p>
      </div>

      <div className={cx("evidence-stage")} id="evidence">
        <div className={cx("stage-label")}><span>Inside CareerLens</span><span className={cx("micro-label")}>Try the example</span></div>
        <article className={cx("proof-sheet")} aria-labelledby="preview-title">
          <header className={cx("sheet-header")}><div><p className={cx("eyebrow")}>Example analysis</p><h2 id="preview-title">Backend Developer</h2></div><span className={cx("sheet-mark", "lens-mark")} aria-hidden="true"></span></header>
          <div className={cx("score-summary")}>
            <div><p className={cx("score-label")}>Job readiness</p><p className={cx("score-value")}>65.1<span>/ 100</span></p><span className={cx("band")}>Developing</span></div>
            <div className={cx("score-orbit")} aria-hidden="true"><svg viewBox="0 0 120 120"><circle className={cx("orbit-track")} cx="60" cy="60" r="49"/><circle className={cx("orbit-value")} cx="60" cy="60" r="49" pathLength="100" strokeDasharray="65.1 100"/></svg></div>
          </div>
          <div className={cx("evidence-heading")}><h3>Skills, with sources.</h3><span>Select a skill</span></div>
          <div className={cx("skill-options")} role="group" aria-label="Example skill evidence">{examples.map((example, index) => <button key={example.name} className={cx("skill-row")} aria-pressed={selected === index} onClick={() => setSelected(index)}><span className={cx("skill-name")}>{example.name}</span><span className={cx("skill-source")}>{example.source}</span><span className={cx("evidence-level", index === 2 ? "moderate" : "")}>{example.level}</span><span className={cx("row-arrow")} aria-hidden="true">↗</span></button>)}</div>
          <div aria-live="polite" aria-atomic="true"><div className={cx("source-note")} key={selected}><p className={cx("source-eyebrow")}>{examples[selected].name} · {examples[selected].level.toLowerCase()} evidence</p><p data-source-reason>{examples[selected].reason}</p><span data-source-location>Source / {examples[selected].source}</span></div></div>
          <div className={cx("sheet-footer")}><span>Evidence coverage</span><strong>62.5%</strong></div>
        </article>
        <p className={cx("example-caption")}>Illustrative example. Synthetic data, real product structure.</p>
      </div>
    </section>

    <section className={cx("work-story", "wrap", "reveal")} aria-labelledby="work-title">
      <div className={cx("story-intro")}><p className={cx("eyebrow")}>A clearer picture</p><h2 id="work-title">More context.<br />Better next moves.</h2></div>
      <div className={cx("story-body")}><p>Skills mean more when you can see the work behind them. CareerLens connects your claims to your projects, explains the gaps, and gives you something useful to do next.</p><p className={cx("quiet")}>A readiness score with reasons. A roadmap with deliverables.</p></div>
      <div className={cx("source-strip")} aria-label="The CareerLens workflow"><span>Your resume</span><span className={cx("path-line")} aria-hidden="true"></span><span>Your work</span><span className={cx("path-line")} aria-hidden="true"></span><span className={cx("strip-final")}>Your next step</span></div>
    </section>

    <section className={cx("next-section", "wrap", "reveal")} id="next-step" aria-labelledby="next-title">
      <div className={cx("next-copy")}><p className={cx("eyebrow")}>Make the next move count</p><h2 id="next-title">Less guessing.<br />Something to build.</h2><p>Turn an evidence gap into a small, concrete piece of work. Your roadmap connects each milestone to the skills it can strengthen.</p><Link className={cx("text-link")} href="/login">Find my next step <span aria-hidden="true">↗</span></Link></div>
      <article className={cx("milestone")} aria-labelledby="milestone-title"><div className={cx("milestone-top")}><span className={cx("micro-label")}>Example milestone</span><span className={cx("effort")}>3 hours estimated</span></div><h3 id="milestone-title">Add CI to<br />campus-api.</h3><p>Run pytest on every push with a GitHub Actions workflow and a passing badge in the README.</p><div className={cx("milestone-meta")}><span>Addresses <strong>CI/CD</strong></span><span>Estimated gain <strong>+4.5 pts</strong></span></div><button className={cx("deliverable-button")} aria-expanded={deliverableOpen} aria-controls="deliverable-detail" onClick={() => setDeliverableOpen(!deliverableOpen)}>Look at the deliverable <span aria-hidden="true">{deliverableOpen ? "−" : "+"}</span></button><div id="deliverable-detail" data-deliverable-detail hidden={!deliverableOpen}><p>Add a workflow file to campus-api that runs pytest on every push. Complete the work, then reanalyse to measure any change in readiness.</p><a href="https://docs.github.com/en/actions" target="_blank" rel="noreferrer">GitHub Actions documentation <span aria-hidden="true">↗</span><span className={cx("sr-only")}> (opens a new tab)</span></a></div><p className={cx("estimate-note")}>Synthetic example. Score gains are estimates, not guarantees.</p></article>
    </section>

    <section className={cx("questions-section", "wrap", "reveal")} id="questions" aria-labelledby="questions-title">
      <div><p className={cx("eyebrow")}>Before you begin</p><h2 id="questions-title">A few good<br />questions.</h2></div>
      <div className={cx("questions-list")}>
        <details><summary>What do I need to get started?<span aria-hidden="true">+</span></summary><p>Sign in with your Google account, then add your resume and relevant project links. GitHub and portfolio work help build the evidence picture.</p></details>
        <details><summary>What does the readiness score tell me?<span aria-hidden="true">+</span></summary><p>It summarises the available evidence for your target role. Its components and reasons explain the result. It is not a hiring probability or a guarantee.</p></details>
        <details><summary>What if I’m just getting started?<span aria-hidden="true">+</span></summary><p>Missing evidence does not prove that you lack a skill. Use the gaps and milestones to decide what to build and document next.</p></details>
        <details><summary>Is evidence coverage the same as readiness?<span aria-hidden="true">+</span></summary><p>No. Evidence coverage describes the percentage of claimed skills with strong or moderate support. Readiness combines the analysis components for your target role.</p></details>
        <details><summary>Do I have to take a project quiz?<span aria-hidden="true">+</span></summary><p>No. Skipping a quiz does not lower your score. A quiz can provide more information about your demonstrated understanding.</p></details>
      </div>
    </section>

    <section className={cx("closing", "wrap", "reveal")} aria-labelledby="closing-title"><div><p className={cx("eyebrow")}>Your work is the starting point</p><h2 id="closing-title">Give it a closer look.</h2></div><Link className={cx("button", "primary")} href="/login">Continue with Google <span aria-hidden="true">↗</span></Link></section>
  </main>
  <footer className={cx("site-footer", "wrap")}><Link className={cx("brand")} href="/" aria-label="CareerLens home"><span className={cx("lens-mark")} aria-hidden="true"></span>CareerLens</Link><p>Built on evidence.</p><Link href="/login">Your workspace <span aria-hidden="true">↗</span></Link></footer><div className={cx("wrap")}><Credit /></div>
</div>;
}
