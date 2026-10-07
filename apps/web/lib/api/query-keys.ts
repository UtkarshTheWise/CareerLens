import type { OperationInputs } from "./operations";
export const queryKeys = {
  getHealth: (input?: OperationInputs["getHealth"]) => [...["health"], input] as const,
  listRoles: (input?: OperationInputs["listRoles"]) => [...["roles"], input] as const,
  getMe: (input?: OperationInputs["getMe"]) => [...["me"], input] as const,
  getProfile: (input?: OperationInputs["getProfile"]) => [...["profiles"], input] as const,
  listAnalyses: (input?: OperationInputs["listAnalyses"]) => [...["analyses"], input] as const,
  getAnalysis: (input?: OperationInputs["getAnalysis"]) => [...["analysis"], input] as const,
  getQuiz: (input?: OperationInputs["getQuiz"]) => [...["quiz"], input] as const,
  getQuizResult: (input?: OperationInputs["getQuizResult"]) => [...["quizResult"], input] as const,
  listQuizzes: (input?: OperationInputs["listQuizzes"]) => [...["quizzes"], input] as const,
  listApplications: (input?: OperationInputs["listApplications"]) => [...["applications"], input] as const,
  listCohorts: (input?: OperationInputs["listCohorts"]) => [...["cohorts"], input] as const,
  getCohortInsights: (input?: OperationInputs["getCohortInsights"]) => [...["cohortInsights"], input] as const,
  listCohortStudents: (input?: OperationInputs["listCohortStudents"]) => [...["cohortStudents"], input] as const,
  exportCohort: (input?: OperationInputs["exportCohort"]) => [...["cohortExport"], input] as const,
};
