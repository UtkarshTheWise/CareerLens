import { FolderSearch } from "lucide-react";
import { PageHeader, Panel, TextLink } from "./page";
// TODO(progress): Feature content is implemented in the owning later F prompt.
export function SectionShell({ title, description }: { title: string; description: string }) {
  return <section>
    <PageHeader eyebrow="Your workspace" title={title} description={description}/>
    <Panel>
      <div className="icon-chip mb-5"><FolderSearch aria-hidden="true" size={20} strokeWidth={1.75}/></div>
      <h2 className="section-title">Your evidence belongs here</h2>
      <p className="lede mt-2">Connect your work to see the skills it supports, and find a clear next step.</p>
      <p className="mt-6"><TextLink href="/dev/roles">Explore target roles</TextLink></p>
    </Panel>
  </section>;
}
