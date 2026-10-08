import Link from "next/link";
import { ArrowUpRight, FolderSearch } from "lucide-react";
// TODO(progress): Feature content is implemented in the owning later F prompt.
export function SectionShell({ title, description }: { title: string; description: string }) {
  return <section className="space-y-8">
    <div><p className="mb-2 text-xs font-medium text-muted-readable">Your workspace</p><h1>{title}</h1><p className="mt-2 max-w-xl text-sm text-muted-readable">{description}</p></div>
    <div className="rounded-card border border-border bg-surface p-6 shadow-card sm:p-8">
      <div className="icon-chip mb-5"><FolderSearch aria-hidden="true" size={20} strokeWidth={1.75}/></div>
      <h2>Your evidence belongs here</h2><p className="mt-2 max-w-lg text-sm text-muted-readable">Connect your work to see the skills it supports, and find a clear next step.</p>
      <Link href="/dev/roles" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary-text">Explore target roles<ArrowUpRight size={16} aria-hidden="true"/></Link>
    </div>
  </section>;
}
