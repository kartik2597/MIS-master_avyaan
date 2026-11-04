import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable, type Column } from "@/shared/components/DataTable/DataTable";
import { ConfirmDeleteButton } from "@/shared/components/ConfirmDelete/ConfirmDeleteButton";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { UploadStatusBadge, humanize } from "@/shared/components/StatusBadge/StatusBadge";
import { KPICard } from "@/shared/components/KPICard/KPICard";
import { cn } from "@/lib/utils";
import { useAuth } from "@/app/store/authStore";
import { getErrorMessage } from "@/lib/api-client";
import { importMasterDatabase } from "@/services/api/imports";
import { deleteUpload, listUploads } from "@/services/api/uploads";
import type { UploadHistory } from "@/services/api/types";
import { AlertTriangle, CheckCircle2, Database, History, ListChecks, Loader2, RefreshCw, RotateCcw, Search } from "lucide-react";
import { UploadIssuesDialog } from "../components/UploadIssuesDialog";

const REPORT_TYPES = [
  "All",
  "APR",
  "SHIFT_ADHERENCE",
  "SHRINKAGE",
  "MASTER_DATABASE",
  "EMPLOYEE_ROSTER",
  "DAILY_ACTIVITY",
  "SHRINKAGE_HOURS",
];
const STATUSES = ["All", "PENDING", "VALIDATED", "VALIDATION_FAILED", "PROCESSING", "COMPLETED", "FAILED"];

const REPORT_LABELS: Record<string, string> = {
  APR: "APR",
  SHIFT_ADHERENCE: "Shift adherence",
  SHRINKAGE: "Shrinkage",
  MASTER_DATABASE: "Master database",
  EMPLOYEE_ROSTER: "Employee roster",
  DAILY_ACTIVITY: "Daily activity",
  SHRINKAGE_HOURS: "Shrinkage hours",
};

const reportLabel = (value: string) => REPORT_LABELS[value] ?? humanize(value);

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const FAILED_STATUSES = ["FAILED", "VALIDATION_FAILED"];

export function UploadHistoryPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canWrite = user?.role === "ADMIN" || user?.role === "MIS";
  const [type, setType] = useState("All");
  const [status, setStatus] = useState("All");
  const [fileSearch, setFileSearch] = useState("");
  const [issuesUploadId, setIssuesUploadId] = useState<string | null>(null);
  const filtered = type !== "All" || status !== "All" || fileSearch.trim() !== "";

  const uploadsQuery = useQuery({
    queryKey: ["uploads", type, status],
    // Keep refreshing while a file is being processed so the status updates itself.
    refetchInterval: (query) =>
      query.state.data?.items.some((row) => row.upload_status === "PROCESSING") ? 3000 : false,
    queryFn: () =>
      listUploads({
        page: 1,
        page_size: 100,
        report_type: type === "All" ? undefined : type,
        upload_status: status === "All" ? undefined : status,
      }),
  });

  const importMutation = useMutation({
    mutationFn: importMasterDatabase,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["uploads"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUpload,
    // A delete removes the imported data too, so refresh everything that shows it.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ["uploads"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["employees"] }),
      ]),
  });

  const allRows = uploadsQuery.data?.items ?? [];
  const query = fileSearch.trim().toLowerCase();
  // File name search runs here, on the (at most 100) rows already loaded.
  const rows = query ? allRows.filter((row) => row.original_file_name.toLowerCase().includes(query)) : allRows;
  const counts = {
    completed: allRows.filter((row) => row.upload_status === "COMPLETED").length,
    failed: allRows.filter((row) => FAILED_STATUSES.includes(row.upload_status)).length,
    processing: allRows.filter((row) => row.upload_status === "PROCESSING").length,
  };

  const columns: Column<UploadHistory>[] = [
    {
      key: "id",
      header: "Upload ID",
      render: (row) => <span className="font-mono text-xs text-muted-foreground">{row.id.slice(0, 8)}</span>,
    },
    {
      key: "original_file_name",
      header: "File Name",
      render: (row) => (
        <div className="min-w-0">
          <p className="font-medium text-foreground">{row.original_file_name}</p>
          {formatBytes(row.file_size) && (
            <p className="text-xs text-muted-foreground">{formatBytes(row.file_size)}</p>
          )}
        </div>
      ),
    },
    { key: "report_type", header: "Report Type", render: (row) => reportLabel(row.report_type) },
    { key: "uploaded_by", header: "Uploaded By" },
    {
      key: "uploaded_at",
      header: "Upload Date",
      className: "whitespace-nowrap",
      render: (row) => new Date(row.uploaded_at).toLocaleString(),
    },
    { key: "total_records", header: "Records", align: "right", render: (row) => row.total_records.toLocaleString() },
    {
      key: "failed_records",
      header: "Failed",
      align: "right",
      render: (row) =>
        row.failed_records > 0 ? (
          <span
            title={row.error_message ?? "Some rows could not be imported"}
            className="font-medium text-destructive tabular-nums cursor-help"
          >
            {row.failed_records.toLocaleString()}
          </span>
        ) : (
          <span className="text-muted-foreground/60">—</span>
        ),
    },
    { key: "upload_status", header: "Status", render: (row) => <UploadStatusBadge status={row.upload_status} /> },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <div className="flex gap-1 justify-end">
          {(row.failed_records > 0 || FAILED_STATUSES.includes(row.upload_status)) && (
            <Button size="sm" variant="outline" onClick={() => setIssuesUploadId(row.id)}>
              <ListChecks className="h-4 w-4 mr-2" /> View issues
            </Button>
          )}
          {canWrite && row.report_type === "MASTER_DATABASE" && (
            <Button
              size="sm"
              variant="outline"
              disabled={importMutation.isPending}
              onClick={() => importMutation.mutate(row.id)}
            >
              <Database className="h-4 w-4 mr-2" /> Import
            </Button>
          )}
          {/* Admin/MIS see every upload; other roles only see their own, so the
              delete button is safe to show on every row they can see. */}
          <ConfirmDeleteButton
            title="Delete upload?"
            description={`This will permanently delete ${row.original_file_name} and all the data imported from it. This cannot be undone.`}
            disabled={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate(row.id)}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Upload History"
        description="Audit log of every file uploaded to MIS Master."
        actions={
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => uploadsQuery.refetch()}
            disabled={uploadsQuery.isFetching}
          >
            <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", uploadsQuery.isFetching && "animate-spin")} /> Refresh
          </Button>
        }
      />

      {allRows.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KPICard label="Uploads" value={(uploadsQuery.data?.total ?? allRows.length).toLocaleString()} icon={History} tone="info" />
          <KPICard label="Completed" value={counts.completed} icon={CheckCircle2} tone="success" />
          <KPICard label="Failed" value={counts.failed} icon={AlertTriangle} tone="destructive" />
          <KPICard label="Processing" value={counts.processing} icon={Loader2} tone="warning" />
        </div>
      )}

      <Card className="p-4 shadow-card">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Report Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger aria-label="Report type"><SelectValue /></SelectTrigger>
              <SelectContent>
                {REPORT_TYPES.map((item) => (
                  <SelectItem key={item} value={item}>{item === "All" ? "All types" : reportLabel(item)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger aria-label="Status"><SelectValue /></SelectTrigger>
              <SelectContent>
                {STATUSES.map((item) => (
                  <SelectItem key={item} value={item}>{item === "All" ? "All statuses" : humanize(item)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="history-file-search" className="text-xs text-muted-foreground">File name</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="history-file-search"
                type="search"
                placeholder="Search files..."
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          <div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={!filtered}
              onClick={() => {
                setType("All");
                setStatus("All");
                setFileSearch("");
              }}
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Reset filters
            </Button>
          </div>
        </div>
      </Card>

      {uploadsQuery.error && !uploadsQuery.data ? (
        <ErrorState
          title="Unable to load upload history"
          message={getErrorMessage(uploadsQuery.error, "Unable to load upload history.")}
        />
      ) : (
        <DataTable
          columns={columns}
          data={rows}
          loading={uploadsQuery.isLoading}
          rowKey={(row) => row.id}
          empty={filtered ? "No uploads match these filters" : "No uploads yet"}
          emptyDescription={filtered ? "Try changing or resetting the filters." : "Uploaded files will be listed here."}
          emptyIcon={History}
        />
      )}

      {importMutation.error && (
        <ErrorState
          title="Import failed"
          message={getErrorMessage(importMutation.error, "Unable to import master database upload.")}
        />
      )}
      {deleteMutation.error && (
        <ErrorState
          title="Delete failed"
          message={getErrorMessage(deleteMutation.error, "Unable to delete upload.")}
        />
      )}
      <UploadIssuesDialog uploadId={issuesUploadId} onClose={() => setIssuesUploadId(null)} />
    </div>
  );
}
