import { apiRequest } from "@/lib/api-client";
import type { Employee, EmployeePayload, Paginated } from "./types";

export interface EmployeeListParams {
  page?: number;
  page_size?: number;
  search?: string;
  department?: string;
  process?: string;
  manager_name?: string;
}

function query(params: EmployeeListParams) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function listEmployees(params: EmployeeListParams = {}) {
  return apiRequest<Paginated<Employee>>(`/employees${query(params)}`);
}

export function createEmployee(payload: EmployeePayload) {
  return apiRequest<Employee>("/employees", {
    method: "POST",
    body: payload,
  });
}

export function updateEmployee(id: string, payload: Partial<EmployeePayload>) {
  return apiRequest<Employee>(`/employees/${id}`, {
    method: "PUT",
    body: payload,
  });
}

export function deleteEmployee(id: string) {
  return apiRequest<void>(`/employees/${id}`, { method: "DELETE" });
}
