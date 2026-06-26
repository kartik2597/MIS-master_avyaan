export type Role = "ADMIN" | "MIS" | "MANAGER";

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreatePayload {
  full_name: string;
  email: string;
  password: string;
  role: Role;
  is_active: boolean;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface DashboardKpis {
  head_count: number;
  present_count: number;
  late_login_count: number;
  early_logout_count: number;
  shift_adherence_count: number;
  non_adherence_count: number;
  planned_shrinkage: number | string;
  unplanned_shrinkage: number | string;
  overall_shrinkage: number | string;
  attrition_count: number;
  total_talk_time: number | string;
  total_login_time: number | string;
  total_staff_time: number | string;
  total_downtime: number | string;
  total_idle_time: number | string;
  total_break_time: number | string;
}

export interface Employee {
  id: string;
  emp_id: string;
  employee_name: string;
  email: string;
  mobile: string;
  department: string;
  process: string;
  designation: string;
  manager_name: string;
  tl_name: string;
  date_of_joining: string;
  employment_status: string;
  location: string;
  created_at: string;
  updated_at: string;
}

export type EmployeePayload = Omit<Employee, "id" | "created_at" | "updated_at">;

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface UploadHistory {
  id: string;
  file_name: string;
  original_file_name: string;
  report_type: string;
  file_size: number;
  uploaded_by: string;
  upload_status: string;
  total_records: number;
  processed_records: number;
  failed_records: number;
  error_message: string | null;
  validation_result: {
    is_valid?: boolean;
    missing_columns?: string[];
    extra_columns?: string[];
    errors?: string[];
  } | null;
  uploaded_at: string;
  processing_started_at: string | null;
  processing_completed_at: string | null;
}

export interface FileUploadDetectionResponse {
  upload_id: string;
  file_name: string;
  detected_report_type: string | null;
  confidence_score: number;
  total_columns: number;
  missing_columns: string[];
}

export interface ImportSummary {
  total_records: number;
  processed_records: number;
  failed_records: number;
}
