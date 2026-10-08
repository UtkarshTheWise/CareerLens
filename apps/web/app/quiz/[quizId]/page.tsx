import { QuizScreen } from "@/components/quiz/quiz-screen";
export default async function Page({
  params,
}: {
  params: Promise<{ quizId: string }>;
}) {
  const { quizId } = await params;
  return <QuizScreen key={quizId} quizId={quizId} />;
}
