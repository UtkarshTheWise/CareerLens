import { AnalysisProgress } from "@/components/analysis/analysis-progress";
export default async function Page({
  params,
}: {
  params: Promise<{ analysisId: string }>;
}) {
  const { analysisId } = await params;
  return <AnalysisProgress key={analysisId} analysisId={analysisId} />;
}
