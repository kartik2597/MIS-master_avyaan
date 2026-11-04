import { apiRequest } from "@/lib/api-client";
import { query, type DashboardKpiParams } from "./dashboard";
import type { HiringEventList, HiringEventType, HiringSummary, HiringTeamList, HiringTrends } from "./types";

export interface HiringEventParams extends DashboardKpiParams {
  event_type?: HiringEventType;
  search?: string;
  page?: number;
  page_size?: number;
}

// With no dates the backend reports the latest 90 days that have hiring or exit data.
export function getHiringSummary(params: DashboardKpiParams = {}) {
  return apiRequest<HiringSummary>(`/dashboard/hiring/summary${query(params)}`);
}

export function getHiringTrends(params: DashboardKpiParams = {}) {
  return apiRequest<HiringTrends>(`/dashboard/hiring/trends${query(params)}`);
}

export function getHiringTeams(params: DashboardKpiParams = {}) {
  return apiRequest<HiringTeamList>(`/dashboard/hiring/teams${query(params)}`);
}

export function getHiringEvents(params: HiringEventParams = {}) {
  return apiRequest<HiringEventList>(`/dashboard/hiring/events${query(params)}`);
}
