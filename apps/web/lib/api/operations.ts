import type { ApiClient, paths } from "@careerlens/api-client";
import { apiClient } from "./client";
import { unwrap } from "./transport";
type Op<P extends keyof paths, M extends keyof paths[P]> = NonNullable<paths[P][M]>;
type PathInput<P extends keyof paths, M extends keyof paths[P]> = Op<P,M> extends { parameters: { path: infer T } } ? T : Record<never, never>;
type QueryInput<P extends keyof paths, M extends keyof paths[P]> = Op<P,M> extends { parameters: { query: infer T } } ? T : Record<never, never>;
type BodyInput<P extends keyof paths, M extends keyof paths[P]> = Op<P,M> extends { requestBody: { content: infer C } } ? C[keyof C] : never;

export type OperationInputs = {
  getHealth: undefined;
  listRoles: undefined;
  getMe: undefined;
  createProfile: { body: BodyInput<"/v1/profiles", "post"> };
  getProfile: PathInput<"/v1/profiles/{profile_id}", "get">;
  updateProfile: PathInput<"/v1/profiles/{profile_id}", "patch"> & { body: BodyInput<"/v1/profiles/{profile_id}", "patch"> };
  deleteProfile: PathInput<"/v1/profiles/{profile_id}", "delete">;
  uploadDocument: PathInput<"/v1/profiles/{profile_id}/documents", "post"> & { body: BodyInput<"/v1/profiles/{profile_id}/documents", "post"> };
  startAnalysis: PathInput<"/v1/profiles/{profile_id}/analyses", "post"> & { body: BodyInput<"/v1/profiles/{profile_id}/analyses", "post"> };
  listAnalyses: PathInput<"/v1/profiles/{profile_id}/analyses", "get">;
  getAnalysis: PathInput<"/v1/analyses/{analysis_id}", "get">;
  simulateAnalysis: PathInput<"/v1/analyses/{analysis_id}/simulate", "post"> & { body: BodyInput<"/v1/analyses/{analysis_id}/simulate", "post"> };
  updateMilestone: PathInput<"/v1/analyses/{analysis_id}/roadmap/{milestone_id}", "patch"> & { body: BodyInput<"/v1/analyses/{analysis_id}/roadmap/{milestone_id}", "patch"> };
  createQuiz: PathInput<"/v1/analyses/{analysis_id}/quizzes", "post"> & { body: BodyInput<"/v1/analyses/{analysis_id}/quizzes", "post"> };
  getQuiz: PathInput<"/v1/quizzes/{quiz_id}", "get">;
  answerQuizQuestion: PathInput<"/v1/quizzes/{quiz_id}/answers", "post"> & { body: BodyInput<"/v1/quizzes/{quiz_id}/answers", "post"> };
  submitQuiz: PathInput<"/v1/quizzes/{quiz_id}/submit", "post">;
  getQuizResult: PathInput<"/v1/quizzes/{quiz_id}/result", "get">;
  listQuizzes: PathInput<"/v1/profiles/{profile_id}/quizzes", "get">;
  matchJob: { body: BodyInput<"/v1/jobs/match", "post"> };
  listApplications: { query: QueryInput<"/v1/applications", "get"> };
  createApplication: { body: BodyInput<"/v1/applications", "post"> };
  updateApplication: PathInput<"/v1/applications/{application_id}", "patch"> & { body: BodyInput<"/v1/applications/{application_id}", "patch"> };
  deleteApplication: PathInput<"/v1/applications/{application_id}", "delete">;
  tailorResume: PathInput<"/v1/applications/{application_id}/tailored-resume", "post">;
  listCohorts: undefined;
  getCohortInsights: PathInput<"/v1/cohorts/{cohort_id}/insights", "get"> & { query: QueryInput<"/v1/cohorts/{cohort_id}/insights", "get"> };
  listCohortStudents: PathInput<"/v1/cohorts/{cohort_id}/students", "get"> & { query: QueryInput<"/v1/cohorts/{cohort_id}/students", "get"> };
  exportCohort: PathInput<"/v1/cohorts/{cohort_id}/export", "get"> & { query: QueryInput<"/v1/cohorts/{cohort_id}/export", "get"> };
};
export function createOperations(client: ApiClient = apiClient) { return {
  getHealth: (signal?: AbortSignal) => unwrap(client.GET("/health", { signal })),
  listRoles: (signal?: AbortSignal) => unwrap(client.GET("/v1/roles", { signal })),
  getMe: (signal?: AbortSignal) => unwrap(client.GET("/v1/me", { signal })),
  createProfile: (input: OperationInputs["createProfile"], signal?: AbortSignal) => unwrap(client.POST("/v1/profiles", { signal, body: input.body })),
  getProfile: (input: OperationInputs["getProfile"], signal?: AbortSignal) => unwrap(client.GET("/v1/profiles/{profile_id}", { signal, params: { path: { profile_id: input.profile_id } } })),
  updateProfile: (input: OperationInputs["updateProfile"], signal?: AbortSignal) => unwrap(client.PATCH("/v1/profiles/{profile_id}", { signal, params: { path: { profile_id: input.profile_id } }, body: input.body })),
  deleteProfile: (input: OperationInputs["deleteProfile"], signal?: AbortSignal) => unwrap(client.DELETE("/v1/profiles/{profile_id}", { signal, params: { path: { profile_id: input.profile_id } } })),
  uploadDocument: (input: OperationInputs["uploadDocument"], signal?: AbortSignal) => unwrap(client.POST("/v1/profiles/{profile_id}/documents", { signal, params: { path: { profile_id: input.profile_id } }, body: input.body, bodySerializer: (body) => { const form = new FormData(); form.set("kind", body.kind); form.set("file", body.file); return form; } })),
  startAnalysis: (input: OperationInputs["startAnalysis"], signal?: AbortSignal) => unwrap(client.POST("/v1/profiles/{profile_id}/analyses", { signal, params: { path: { profile_id: input.profile_id } }, body: input.body })),
  listAnalyses: (input: OperationInputs["listAnalyses"], signal?: AbortSignal) => unwrap(client.GET("/v1/profiles/{profile_id}/analyses", { signal, params: { path: { profile_id: input.profile_id } } })),
  getAnalysis: (input: OperationInputs["getAnalysis"], signal?: AbortSignal) => unwrap(client.GET("/v1/analyses/{analysis_id}", { signal, params: { path: { analysis_id: input.analysis_id } } })),
  simulateAnalysis: (input: OperationInputs["simulateAnalysis"], signal?: AbortSignal) => unwrap(client.POST("/v1/analyses/{analysis_id}/simulate", { signal, params: { path: { analysis_id: input.analysis_id } }, body: input.body })),
  updateMilestone: (input: OperationInputs["updateMilestone"], signal?: AbortSignal) => unwrap(client.PATCH("/v1/analyses/{analysis_id}/roadmap/{milestone_id}", { signal, params: { path: { analysis_id: input.analysis_id, milestone_id: input.milestone_id } }, body: input.body })),
  createQuiz: (input: OperationInputs["createQuiz"], signal?: AbortSignal) => unwrap(client.POST("/v1/analyses/{analysis_id}/quizzes", { signal, params: { path: { analysis_id: input.analysis_id } }, body: input.body })),
  getQuiz: (input: OperationInputs["getQuiz"], signal?: AbortSignal) => unwrap(client.GET("/v1/quizzes/{quiz_id}", { signal, params: { path: { quiz_id: input.quiz_id } } })),
  answerQuizQuestion: (input: OperationInputs["answerQuizQuestion"], signal?: AbortSignal) => unwrap(client.POST("/v1/quizzes/{quiz_id}/answers", { signal, params: { path: { quiz_id: input.quiz_id } }, body: input.body })),
  submitQuiz: (input: OperationInputs["submitQuiz"], signal?: AbortSignal) => unwrap(client.POST("/v1/quizzes/{quiz_id}/submit", { signal, params: { path: { quiz_id: input.quiz_id } } })),
  getQuizResult: (input: OperationInputs["getQuizResult"], signal?: AbortSignal) => unwrap(client.GET("/v1/quizzes/{quiz_id}/result", { signal, params: { path: { quiz_id: input.quiz_id } } })),
  listQuizzes: (input: OperationInputs["listQuizzes"], signal?: AbortSignal) => unwrap(client.GET("/v1/profiles/{profile_id}/quizzes", { signal, params: { path: { profile_id: input.profile_id } } })),
  matchJob: (input: OperationInputs["matchJob"], signal?: AbortSignal) => unwrap(client.POST("/v1/jobs/match", { signal, body: input.body })),
  listApplications: (input: OperationInputs["listApplications"], signal?: AbortSignal) => unwrap(client.GET("/v1/applications", { signal, params: { query: input.query } })),
  createApplication: (input: OperationInputs["createApplication"], signal?: AbortSignal) => unwrap(client.POST("/v1/applications", { signal, body: input.body })),
  updateApplication: (input: OperationInputs["updateApplication"], signal?: AbortSignal) => unwrap(client.PATCH("/v1/applications/{application_id}", { signal, params: { path: { application_id: input.application_id } }, body: input.body })),
  deleteApplication: (input: OperationInputs["deleteApplication"], signal?: AbortSignal) => unwrap(client.DELETE("/v1/applications/{application_id}", { signal, params: { path: { application_id: input.application_id } } })),
  tailorResume: (input: OperationInputs["tailorResume"], signal?: AbortSignal) => unwrap(client.POST("/v1/applications/{application_id}/tailored-resume", { signal, params: { path: { application_id: input.application_id } } })),
  listCohorts: (signal?: AbortSignal) => unwrap(client.GET("/v1/cohorts", { signal })),
  getCohortInsights: (input: OperationInputs["getCohortInsights"], signal?: AbortSignal) => unwrap(client.GET("/v1/cohorts/{cohort_id}/insights", { signal, params: { path: { cohort_id: input.cohort_id }, query: input.query } })),
  listCohortStudents: (input: OperationInputs["listCohortStudents"], signal?: AbortSignal) => unwrap(client.GET("/v1/cohorts/{cohort_id}/students", { signal, params: { path: { cohort_id: input.cohort_id }, query: input.query } })),
  exportCohort: (input: OperationInputs["exportCohort"], signal?: AbortSignal) => unwrap(client.GET("/v1/cohorts/{cohort_id}/export", { signal, params: { path: { cohort_id: input.cohort_id }, query: input.query }, parseAs: "text" })),
}; }
export const operations = createOperations();
