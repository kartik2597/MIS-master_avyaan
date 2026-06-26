import { apiRequest } from "@/lib/api-client";
import type { ImportSummary } from "./types";

export function importMasterDatabase(uploadId: string) {
  return apiRequest<ImportSummary>(`/imports/master-database/${uploadId}`, {
    method: "POST",
  });
}
