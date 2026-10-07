"use client";
import { BookOpen, RefreshCw, ArrowUpRight, CircleAlert } from "lucide-react";
import { useListRoles } from "@/lib/api/hooks";
import { apiBaseUrl } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/transport";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
export default function RolesPage() {
  const roles = useListRoles();
  return <section className="space-y-8">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="mb-2 text-xs font-medium text-muted-readable">Build toward a role</p><h1>Find your direction.</h1><p className="mt-2 max-w-xl text-sm text-muted-readable">Explore the skills each role calls for. Your evidence will show where you stand.</p></div>
      <Button variant="outline" className="shrink-0 rounded-control bg-surface" disabled={roles.isFetching} onClick={() => void roles.refetch()}><RefreshCw className={roles.isFetching ? "animate-spin" : ""} aria-hidden="true"/>Refresh roles</Button>
    </div>
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 rounded-control border border-border bg-surface px-4 py-3 text-xs text-muted-readable"><span className="font-medium text-text">API wiring preview</span><span className="min-w-0 break-all">GET {apiBaseUrl}/v1/roles</span></div>
    {roles.isPending && <div className="grid gap-4 md:grid-cols-2" role="status" aria-label="Loading roles">{Array.from({length: 4}, (_, index) => <Skeleton key={index} className="h-64 rounded-card"/>)}</div>}
    {roles.isError && <div role="alert" className="rounded-card border border-border bg-surface p-6"><CircleAlert size={20} className="mb-4 text-danger" aria-hidden="true"/><h2>Roles could not load</h2><p className="mt-2 text-sm text-muted-readable">{errorMessage(roles.error)}</p><Button className="mt-5" onClick={() => void roles.refetch()} disabled={roles.isFetching}>Try again</Button></div>}
    {roles.isSuccess && roles.data.length === 0 && <div className="rounded-card border border-border bg-surface p-6"><h2>No roles available yet</h2><p className="mt-2 text-sm text-muted-readable">The catalogue is empty. Check back after roles have been added.</p></div>}
    {roles.isSuccess && roles.data.length > 0 && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {roles.data.map(role => <article key={role.id} className="min-w-0 rounded-card border border-border bg-surface p-6 shadow-card">
        <div className="mb-6 flex items-center justify-between"><span className="icon-chip text-primary-text"><BookOpen size={20} strokeWidth={1.75} aria-hidden="true"/></span><span className="rounded-full bg-surface-2 px-3 py-1 text-xs font-medium text-muted-readable">{role.category}</span></div>
        <h2>{role.name}</h2><p className="mt-1 text-xs text-muted-readable">{role.id}</p>
        <div className="mt-6 border-t border-border pt-4"><p className="mb-3 text-xs font-medium text-muted-readable">Skills that matter</p><ul className="space-y-3">{role.skills.map(skill => <li key={skill.skill_id} className="flex items-center justify-between gap-4 text-sm"><span className="min-w-0 break-words">{skill.skill_name}</span><span className="shrink-0 text-xs text-muted-readable">Weight {skill.importance}</span></li>)}</ul></div>
        <div className="mt-6 flex items-center gap-2 text-xs font-medium text-primary-text">Evidence guides your next step<ArrowUpRight size={14} aria-hidden="true"/></div>
      </article>)}
    </div>}
  </section>;
}
