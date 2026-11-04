import { apiRequest } from "@/lib/api-client";
import type { ImportSummary } from "./types";

export const IMPORTABLE_REPORT_TYPES = [
  "APR",
  "SHIFT_ADHERENCE",
  "SHRINKAGE",
  "MASTER_DATABASE",
  "EMPLOYEE_ROSTER",
  "DAILY_ACTIVITY",
  "SHRINKAGE_HOURS",
];

/** Order to process several reports from one workbook: people first, then activity, then shrinkage. */
export const IMPORT_ORDER = ["MASTER_DATABASE", "EMPLOYEE_ROSTER", "DAILY_ACTIVITY", "SHRINKAGE_HOURS"];

export function importReport(reportType: string, uploadId: string) {
  return apiRequest<ImportSummary>(`/imports/${reportType}/${uploadId}`, {
    method: "POST",
  });
}

export function importMasterDatabase(uploadId: string) {
  return apiRequest<ImportSummary>(`/imports/master-database/${uploadId}`, {
    method: "POST",
  });
}
