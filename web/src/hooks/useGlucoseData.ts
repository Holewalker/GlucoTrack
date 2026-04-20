import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Period } from "../api/client";

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: api.settings,
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}

export function useCurrentGlucose() {
  return useQuery({
    queryKey: ["glucose", "current"],
    queryFn: api.current,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useHistory(period: Period) {
  return useQuery({
    queryKey: ["glucose", "history", period],
    queryFn: () => api.history(period),
  });
}

export function useTimeInRange(period: Period) {
  return useQuery({
    queryKey: ["stats", "tir", period],
    queryFn: () => api.timeInRange(period),
  });
}

export function useHourlyPatterns(period: Period) {
  return useQuery({
    queryKey: ["stats", "hourly", period],
    queryFn: () => api.hourlyPatterns(period),
  });
}

export function useEvents(period: Period) {
  return useQuery({
    queryKey: ["stats", "events", period],
    queryFn: () => api.events(period),
  });
}

export function useOverlay(period: Period, groupBy: "day" | "week" | "month") {
  return useQuery({
    queryKey: ["glucose", "overlay", period, groupBy],
    queryFn: () => api.overlay(period, groupBy),
  });
}

export function useRefreshDashboard() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["glucose"] });
    queryClient.invalidateQueries({ queryKey: ["stats"] });
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };
}

export function useActiveAlert() {
  return useQuery({
    queryKey: ["alerts", "active"],
    queryFn: api.activeAlert,
    refetchInterval: 30_000,
    retry: false,
  });
}

export function useAlerts(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["alerts", "list", params],
    queryFn: () => api.alerts(params),
  });
}

export function useAlertStats(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["alerts", "stats", params],
    queryFn: () => api.alertStats(params),
  });
}

export function useUpdateAlertFeedback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, feedback }: { id: number; feedback: string }) =>
      api.patchAlertFeedback(id, feedback),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

export function useTelegramRecipients() {
  return useQuery({
    queryKey: ["telegram", "recipients"],
    queryFn: api.telegramRecipients,
  });
}

export function useCreateRecipient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createRecipient,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["telegram", "recipients"] }),
  });
}

export function useUpdateRecipient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.updateRecipient(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["telegram", "recipients"] }),
  });
}

export function useDeleteRecipient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteRecipient(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["telegram", "recipients"] }),
  });
}

export function useDetectChatId() {
  return useMutation({ mutationFn: api.detectChatId });
}

export function useSendTest() {
  return useMutation({ mutationFn: api.sendTest });
}
