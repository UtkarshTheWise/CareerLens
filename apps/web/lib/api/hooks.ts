"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { operations, type OperationInputs } from "./operations";
import { analysisPollInterval } from "./transport";
import { queryKeys } from "./query-keys";
type QueryControl = { enabled?: boolean };

export function useGetHealth(control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getHealth(), queryFn: ({ signal }) => operations.getHealth(signal), enabled: (control.enabled ?? true) }); }
export function useListRoles(control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.listRoles(), queryFn: ({ signal }) => operations.listRoles(signal), enabled: (control.enabled ?? true) }); }
export function useGetMe(control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getMe(), queryFn: ({ signal }) => operations.getMe(signal), enabled: (control.enabled ?? true) }); }
export function useCreateProfile() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["createProfile"]) => operations.createProfile(input),
    onSuccess: async () => { await Promise.all(["profiles", "me"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useGetProfile(input: OperationInputs["getProfile"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getProfile(input), queryFn: ({ signal }) => operations.getProfile(input!, signal), enabled: Boolean(input?.profile_id) && (control.enabled ?? true) }); }
export function useUpdateProfile() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["updateProfile"]) => operations.updateProfile(input),
    onSuccess: async () => { await Promise.all(["profiles", "me"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useDeleteProfile() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["deleteProfile"]) => operations.deleteProfile(input),
    onSuccess: async () => { await Promise.all(["profiles", "me", "analysis", "analyses", "applications", "quiz", "quizzes", "quizResult"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useUploadDocument() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["uploadDocument"]) => operations.uploadDocument(input),
    onSuccess: async () => { await Promise.all(["profiles", "me"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useStartAnalysis() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["startAnalysis"]) => operations.startAnalysis(input),
    onSuccess: async () => { await Promise.all(["analyses"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useListAnalyses(input: OperationInputs["listAnalyses"] | undefined, control: QueryControl & { staleTime?: number } = {}) { return useQuery({ queryKey: queryKeys.listAnalyses(input), queryFn: ({ signal }) => operations.listAnalyses(input!, signal), enabled: Boolean(input?.profile_id) && (control.enabled ?? true), ...(control.staleTime === undefined ? {} : { staleTime: control.staleTime }) }); }
export function useGetAnalysis(input: OperationInputs["getAnalysis"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getAnalysis(input), queryFn: ({ signal }) => operations.getAnalysis(input!, signal), enabled: Boolean(input?.analysis_id) && (control.enabled ?? true), refetchInterval: (query) => query.state.status === "error" ? false : analysisPollInterval(query.state.data) }); }
export function useSimulateAnalysis() { return useMutation({ mutationFn: (input: OperationInputs["simulateAnalysis"]) => operations.simulateAnalysis(input) }); }
export function useUpdateMilestone() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["updateMilestone"]) => operations.updateMilestone(input),
    onSuccess: async () => { await Promise.all(["analysis"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useCreateQuiz() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["createQuiz"]) => operations.createQuiz(input),
    onSuccess: async () => { await Promise.all(["quiz", "quizzes", "quizResult"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useGetQuiz(input: OperationInputs["getQuiz"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getQuiz(input), queryFn: ({ signal }) => operations.getQuiz(input!, signal), enabled: Boolean(input?.quiz_id) && (control.enabled ?? true) }); }
export function useAnswerQuizQuestion() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["answerQuizQuestion"]) => operations.answerQuizQuestion(input),
    onSuccess: async () => { await Promise.all(["quiz", "quizzes", "quizResult"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useSubmitQuiz() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["submitQuiz"]) => operations.submitQuiz(input),
    onSuccess: async () => { await Promise.all(["quiz", "quizzes", "quizResult", "analysis", "analyses", "profiles", "cohortInsights", "cohortStudents"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useGetQuizResult(input: OperationInputs["getQuizResult"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getQuizResult(input), queryFn: ({ signal }) => operations.getQuizResult(input!, signal), enabled: Boolean(input?.quiz_id) && (control.enabled ?? true) }); }
export function useListQuizzes(input: OperationInputs["listQuizzes"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.listQuizzes(input), queryFn: ({ signal }) => operations.listQuizzes(input!, signal), enabled: Boolean(input?.profile_id) && (control.enabled ?? true) }); }
export function useMatchJob() { return useMutation({ mutationFn: (input: OperationInputs["matchJob"]) => operations.matchJob(input) }); }
export function useListApplications(input: OperationInputs["listApplications"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.listApplications(input), queryFn: ({ signal }) => operations.listApplications(input!, signal), enabled: Boolean(input?.query.profile_id) && (control.enabled ?? true) }); }
export function useCreateApplication() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["createApplication"]) => operations.createApplication(input),
    onSuccess: async () => { await Promise.all(["applications"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useUpdateApplication() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["updateApplication"]) => operations.updateApplication(input),
    onSuccess: async () => { await Promise.all(["applications"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useDeleteApplication() {
  const cache = useQueryClient(); return useMutation({
    mutationFn: (input: OperationInputs["deleteApplication"]) => operations.deleteApplication(input),
    onSuccess: async () => { await Promise.all(["applications"].map(key => cache.invalidateQueries({ queryKey: [key] }))); },
  });
}
export function useTailorResume() { return useMutation({ mutationFn: (input: OperationInputs["tailorResume"]) => operations.tailorResume(input) }); }
export function useListCohorts(control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.listCohorts(), queryFn: ({ signal }) => operations.listCohorts(signal), enabled: (control.enabled ?? true) }); }
export function useGetCohortInsights(input: OperationInputs["getCohortInsights"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.getCohortInsights(input), queryFn: ({ signal }) => operations.getCohortInsights(input!, signal), enabled: Boolean(input?.cohort_id) && Boolean(input?.query.role_id) && (control.enabled ?? true) }); }
export function useListCohortStudents(input: OperationInputs["listCohortStudents"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.listCohortStudents(input), queryFn: ({ signal }) => operations.listCohortStudents(input!, signal), enabled: Boolean(input?.cohort_id) && Boolean(input?.query.role_id) && (control.enabled ?? true) }); }
export function useExportCohort(input: OperationInputs["exportCohort"] | undefined, control: QueryControl = {}) { return useQuery({ queryKey: queryKeys.exportCohort(input), queryFn: ({ signal }) => operations.exportCohort(input!, signal), enabled: Boolean(input?.cohort_id) && Boolean(input?.query.role_id) && (control.enabled ?? false) }); }
