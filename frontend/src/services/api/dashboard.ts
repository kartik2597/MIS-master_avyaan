import { apiRequest } from "@/lib/api-client";
import type {
  AttendanceBreakdown,
  DashboardAgentList,
  DashboardFilterOptions,
  DashboardKpis,
  DashboardTrends,
} from "./types";

export interface DashboardKpiParams {
  date_from?: string; // YYYY-MM-DD
  date_to?: string; // YYYY-MM-DD
  // Team filters. Leave out (or "") for everyone the viewer may see.
  process?: string;
  manager?: string;
  tl?: string;
  emp_id?: string;
}

export interface DashboardAgentParams extends DashboardKpiParams {
  search?: string;
  page?: number;
  page_size?: number;
}

export function query(params: object) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

// With no dates the backend reports the latest day that has data.
export function getDashboardKpis(params: DashboardKpiParams = {}) {
  return apiRequest<DashboardKpis>(`/dashboard/kpis${query(params)}`);
}

// With no dates the backend returns the last 30 days that have data.
export function getDashboardTrends(params: DashboardKpiParams = {}) {
  return apiRequest<DashboardTrends>(`/dashboard/trends${query(params)}`);
}

export function getDashboardAttendance(params: DashboardKpiParams = {}) {
  return apiRequest<AttendanceBreakdown>(`/dashboard/attendance${query(params)}`);
}

export function getDashboardAgents(params: DashboardAgentParams = {}) {
  return apiRequest<DashboardAgentList>(`/dashboard/agents${query(params)}`);
}

// Process / manager / TL names for the filter drop-downs (limited to the viewer's team).
export function getDashboardFilterOptions() {
  return apiRequest<DashboardFilterOptions>("/dashboard/filters");
}
