import { apiRequest } from "@/lib/api-client";
import type {
  FileUploadDetectionResponse,
  Paginated,
  UploadHistory,
  UploadValidationReport,
} from "./types";

export interface UploadListParams {
  page?: number;
  page_size?: number;
  report_type?: string;
  upload_status?: string;
}

function query(params: UploadListParams) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function uploadFile(file: File) {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<FileUploadDetectionResponse>("/uploads/file", {
    method: "POST",
    body,
  });
}

export function listUploads(params: UploadListParams = {}) {
  return apiRequest<Paginated<UploadHistory>>(`/uploads${query(params)}`);
}

export function deleteUpload(id: string) {
  return apiRequest<void>(`/uploads/${id}`, { method: "DELETE" });
}

// Column problems and every skipped row ("row 45: invalid date") for one upload.
export function getUploadValidation(id: string) {
  return apiRequest<UploadValidationReport>(`/uploads/${id}/validation`);
}
