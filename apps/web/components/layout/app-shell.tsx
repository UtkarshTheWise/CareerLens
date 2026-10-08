"use client";
import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, FileSearch, Route, BriefcaseBusiness, GraduationCap, Settings, Menu, ArrowUpRight, ScanLine, ChevronRight, LogOut } from "lucide-react";
import { useGetMe } from "@/lib/api/hooks";
import { displayName, useAuth } from "@/components/auth/auth-provider";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from "@/components/ui/sheet";
import { ThemeToggle } from "./theme-toggle";
const destinations = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { title: "Report", href: "/report", icon: FileSearch },
  { title: "Roadmap", href: "/roadmap", icon: Route },
  { title: "Tracker", href: "/tracker", icon: BriefcaseBusiness },
  { title: "Placement cell", href: "/placement", icon: GraduationCap },
  { title: "Settings", href: "/settings", icon: Settings },
];
function Brand() {
  return <Link href="/dashboard" className="flex items-center gap-3 text-lg font-bold tracking-tight" aria-label="CareerLens dashboard">
    <span className="flex size-10 shrink-0 items-center justify-center rounded-control bg-primary text-primary-foreground"><ScanLine size={24} strokeWidth={1.75} aria-hidden="true"/></span>CareerLens
  </Link>;
}
function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname(); const { data: profile } = useGetMe();
  return <nav aria-label="Main navigation" className="space-y-2">
    {destinations.map(({ title, href, icon: Icon }) => {
      const active = pathname === href || pathname.startsWith(href + "/");
      const target = href === "/report" ? (profile?.latest_analysis_id ? `/report/${encodeURIComponent(profile.latest_analysis_id)}` : null) : href;
      if (!target) return <span key={href} className="nav-link text-muted-readable" aria-disabled="true" title="Analyse a profile to open a report"><Icon size={20} strokeWidth={1.75} aria-hidden="true"/>{title}<span className="sr-only"> — an analysis is required</span></span>;
      return <Link key={href} href={target} onClick={onNavigate} className={`nav-link ${active ? "text-primary-foreground" : "text-muted-readable"}`} aria-current={active ? "page" : undefined}><Icon size={20} strokeWidth={1.75} aria-hidden="true"/>{title}{active && <ChevronRight className="ml-auto" size={16} aria-hidden="true"/>}</Link>;
    })}
  </nav>;
}
function ProfileChip() {
  const profile = useGetMe(); const { user } = useAuth();
  if (profile.isPending) return <Skeleton className="h-10 w-24 rounded-control sm:w-40" role="status" aria-label="Loading profile"/>;
  // A signed-in person without a profile yet is shown by their Google name instead of an error.
  const name = profile.data?.name || displayName(user);
  const noProfileYet = profile.isError && profile.error instanceof ApiError && profile.error.status === 404 && Boolean(user);
  const failure = profile.isError && !noProfileYet ? errorMessage(profile.error) : undefined;
  return <Link href="/settings" title={failure} className="flex min-w-0 items-center gap-3 rounded-control px-2 py-1.5 hover:bg-surface-2" aria-label={name ? `Profile settings for ${name}` : `Profile settings${failure ? `. ${failure}` : ""}`}>
    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-chip-text" aria-hidden="true">{name?.trim().charAt(0).toUpperCase() || "?"}</span>
    <span className="hidden min-w-0 sm:block"><span className="block max-w-40 truncate text-sm font-semibold">{name || "Profile unavailable"}</span><span className="block max-w-40 truncate text-xs text-muted-readable">{failure || profile.data?.department || "Your workspace"}</span></span>
  </Link>;
}
export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false); const pathname = usePathname(); const router = useRouter(); const auth = useAuth();
  const bare = pathname === "/login" || pathname.startsWith("/auth/");
  useEffect(() => { if (auth.status === "signed-out" && !bare) router.replace("/login"); }, [auth.status, bare, router]);
  // Sign-in pages stand alone. When sign-in is on, nothing else renders (and no API call is made) until a session exists.
  if (bare) return <>{children}</>;
  if (auth.status === "loading" || auth.status === "signed-out") return <div className="flex min-h-dvh items-center justify-center"><p role="status" className="text-sm text-muted-readable">Checking your session…</p></div>;
  const title = pathname.startsWith("/onboarding") ? "Profile setup" : pathname.startsWith("/dev/components") ? "Component kit" : pathname.startsWith("/dev/roles") ? "Target roles" : destinations.find(item => pathname.startsWith(item.href))?.title || "CareerLens";
  return <div className="min-h-dvh lg:grid lg:grid-cols-[280px_minmax(0,1fr)]">
    <a href="#main-content" className="fixed top-3 left-3 z-50 -translate-y-24 rounded-control bg-primary px-4 py-3 text-primary-foreground focus:translate-y-0">Skip to content</a>
    <aside className="sticky top-0 hidden h-dvh flex-col border-r border-border bg-surface p-6 lg:flex">
      <Brand/><div className="mt-8"><Link href="/onboarding" className="nav-link bg-surface-2 text-primary-text">Analyse a profile<ArrowUpRight size={16} aria-hidden="true"/></Link></div><div className="mt-8"><p className="mb-4 px-4 text-xs font-medium text-muted-readable">Workspace</p><Navigation/></div>
      <div className="mt-auto border-t border-border pt-6"><p className="text-sm font-semibold">Built on evidence.</p><p className="mt-1 text-xs text-muted-readable">Your work tells your story.</p><Link href="/dev/roles" className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-primary-text">Explore target roles<ArrowUpRight size={14} aria-hidden="true"/></Link></div>
    </aside>
    <div className="min-w-0">
      <header className="flex h-24 items-center justify-between gap-3 border-b border-border px-4 sm:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild><Button variant="ghost" size="icon" className="size-10 shrink-0 rounded-control bg-surface lg:hidden" aria-label="Open navigation"><Menu size={20} aria-hidden="true"/></Button></SheetTrigger>
            <SheetContent side="left" className="w-[min(280px,calc(100vw-32px))] gap-0 p-6"><SheetHeader className="p-0 pb-8"><SheetTitle>CareerLens</SheetTitle><SheetDescription>Your evidence workspace</SheetDescription></SheetHeader><Navigation onNavigate={() => setOpen(false)}/></SheetContent>
          </Sheet>
          <p className="truncate text-sm font-semibold">{title}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-4"><ThemeToggle/><div className="h-8 w-px bg-border"/><ProfileChip/>{auth.status === "signed-in" && <Button variant="ghost" size="icon" className="size-10 shrink-0 rounded-control" aria-label="Sign out" title="Sign out" onClick={() => void auth.signOut()}><LogOut size={18} aria-hidden="true"/></Button>}</div>
      </header>
      <main id="main-content" tabIndex={-1} className="mx-auto max-w-[1440px] p-4 outline-none sm:p-8 lg:p-10">{children}</main>
    </div>
  </div>;
}
