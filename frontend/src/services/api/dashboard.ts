import { apiRequest } from "@/lib/api-client";
import type { DashboardKpis } from "./types";

export function getDashboardKpis() {
  return apiRequest<DashboardKpis>("/dashboard/kpis");
}
