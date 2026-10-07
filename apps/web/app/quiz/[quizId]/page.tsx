import Link from "next/link";
import { Button } from "@/components/ui/button";
// TODO(progress): F9 replaces this F4 navigation destination with quiz intro/questions/results.
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ analysis?: string }>;
}) {
  const { analysis } = await searchParams;
  return (
    <section className="max-w-xl space-y-4 rounded-card border border-border bg-surface p-6">
      <h1 className="text-2xl font-semibold">Project understanding check</h1>
      <p className="text-sm leading-relaxed text-muted-readable">
        Your project check has been requested. Keep this URL to return to it.
      </p>
      <Button asChild variant="outline" className="min-h-11">
        <Link
          href={
            analysis ? `/report/${encodeURIComponent(analysis)}` : "/dashboard"
          }
        >
          Return to your report
        </Link>
      </Button>
    </section>
  );
}
