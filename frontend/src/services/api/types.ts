export type Role = "ADMIN" | "MIS" | "MANAGER" | "TL";

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  /** Employee ID this login belongs to. MANAGER and TL users only see their own team. */
  emp_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreatePayload {
  full_name: string;
  email: string;
  password: string;
  role: Role;
  is_active: boolean;
  emp_id?: string | null;
}

export interface Token {
  access_token: string;
  refresh_token?: string | null;
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
  /** The single day every card describes when no date range was requested. */
  report_date?: string | null;
  /** Reports (APR, SHIFT_ADHERENCE, SHRINKAGE) with no rows for the selected day or range. */
  missing_reports?: string[];
}

export interface DashboardFilterOptions {
  processes: string[];
  managers: string[];
  tls: string[];
}

export interface DashboardTrendPoint {
  report_date: string; // YYYY-MM-DD
  head_count: number;
  present_count: number;
  /** 0-100, or null on a day with no shift adherence rows. */
  adherence_percent: number | null;
  /** 0-100, or null on a day with no shrinkage rows. */
  overall_shrinkage: number | null;
  /** Hours. */
  talk_time: number;
  /** Hours. */
  staff_time: number;
}

export interface DashboardTrends {
  points: DashboardTrendPoint[];
}

export interface AttendanceSlice {
  status: string;
  count: number;
}

export interface AttendanceBreakdown {
  slices: AttendanceSlice[];
  total: number;
  report_date?: string | null;
}

export interface DashboardAgentRow {
  emp_id: string;
  employee_name: string;
  process: string;
  days_recorded: number;
  days_present: number;
  /** Hours. */
  login_hours: number;
  talk_time: number;
  idle_time: number;
  break_time: number;
  late_logins: number;
  early_logouts: number;
  adherent_days: number;
}

export interface DashboardAgentList extends Paginated<DashboardAgentRow> {
  report_date?: string | null;
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

/** Mirrors backend `ReportValidationResult`, stored as JSON on the upload record. */
export interface ReportValidationResult {
  valid: boolean;
  missing_columns: string[];
  extra_columns: string[];
  /** 0-100: share of required columns found in the file. */
  validation_score: number;
  sheet_name?: string | null;
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
  validation_result: ReportValidationResult | null;
  uploaded_at: string;
  processing_started_at: string | null;
  processing_completed_at: string | null;
}

/** One row an import skipped. Row 0 means the problem is about the file as a whole. */
export interface RowErrorItem {
  row: number;
  reason: string;
}

/** Mirrors backend `UploadValidationReport`: column problems first, then skipped rows. */
export interface UploadValidationReport {
  upload_id: string;
  original_file_name: string;
  report_type: string;
  upload_status: string;
  uploaded_by_name?: string | null;
  uploaded_at: string;
  sheet_name?: string | null;
  columns_valid: boolean | null;
  validation_score: number | null;
  missing_columns: string[];
  extra_columns: string[];
  total_records: number;
  processed_records: number;
  failed_records: number;
  error_message: string | null;
  row_errors: RowErrorItem[];
  /** True when more rows failed than are listed (the stored list is capped). */
  row_errors_truncated: boolean;
}

/** One report found in an uploaded file: a sheet of a workbook, or a CSV. */
export interface SheetUploadResult {
  upload_id: string;
  sheet_name: string | null;
  detected_report_type: string | null;
  confidence_score: number;
  total_columns: number;
  total_records: number;
  missing_columns: string[];
}

export interface FileUploadDetectionResponse {
  /** The first report found in the file. */
  upload_id: string;
  file_name: string;
  detected_report_type: string | null;
  confidence_score: number;
  total_columns: number;
  missing_columns: string[];
  /** Every report found in the file (one per recognised sheet). */
  sheets?: SheetUploadResult[];
  /** Sheets that matched no report type and were skipped. */
  ignored_sheets?: string[];
}

export interface ImportSummary {
  total_records: number;
  processed_records: number;
  failed_records: number;
  /** Which rows were skipped and why. Null when nothing failed. */
  message?: string | null;
}
