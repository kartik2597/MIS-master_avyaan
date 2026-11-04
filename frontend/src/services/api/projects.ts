import { apiRequest } from "@/lib/api-client";
import { query, type DashboardKpiParams } from "./dashboard";
import type {
  BenchList,
  ProjectEmployeeList,
  ProjectHoursList,
  ProjectSummary,
  ProjectTrends,
} from "./types";

export interface ProjectListParams extends DashboardKpiParams {
  search?: string;
  page?: number;
  page_size?: number;
}

// With no dates the backend reports the latest 30 days that have timesheet data.
export function getProjectSummary(params: DashboardKpiParams = {}) {
  return apiRequest<ProjectSummary>(`/dashboard/projects/summary${query(params)}`);
}

export function getProjectHours(params: DashboardKpiParams & { limit?: number } = {}) {
  return apiRequest<ProjectHoursList>(`/dashboard/projects/projects${query(params)}`);
}

export function getProjectEmployees(params: ProjectListParams = {}) {
  return apiRequest<ProjectEmployeeList>(`/dashboard/projects/employees${query(params)}`);
}

export function getProjectBench(params: ProjectListParams = {}) {
  return apiRequest<BenchList>(`/dashboard/projects/bench${query(params)}`);
}

export function getProjectTrends(params: DashboardKpiParams = {}) {
  return apiRequest<ProjectTrends>(`/dashboard/projects/trends${query(params)}`);
}
