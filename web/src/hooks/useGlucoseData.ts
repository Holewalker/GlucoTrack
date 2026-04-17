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
