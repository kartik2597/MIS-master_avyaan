import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable } from "@/shared/components/DataTable/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/app/store/authStore";
import { importMasterDatabase } from "@/services/api/imports";
import { deleteUpload, listUploads } from "@/services/api/uploads";
import type { UploadHistory } from "@/services/api/types";
import { Database, Trash2 } from "lucide-react";

const REPORT_TYPES = ["All", "APR", "SHIFT_ADHERENCE", "SHRINKAGE", "MASTER_DATABASE"];
const STATUSES = ["All", "PENDING", "VALIDATED", "VALIDATION_FAILED", "PROCESSING", "COMPLETED", "FAILED"];

const statusColor: Record<string, string> = {
  COMPLETED: "bg-success/15 text-success",
  VALIDATED: "bg-info/15 text-info",
  PROCESSING: "bg-warning/20 text-warning-foreground",
  PENDING: "bg-muted text-muted-foreground",
  FAILED: "bg-destructive/15 text-destructive",
  VALIDATION_FAILED: "bg-destructive/15 text-destructive",
};

export function UploadHistoryPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canWrite = user?.role === "ADMIN" || user?.role === "MIS";
  const [type, setType] = useState("All");
  const [status, setStatus] = useState("All");

  const uploadsQuery = useQuery({
    queryKey: ["uploads", type, status],
    queryFn: () => listUploads({
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["uploads"] }),
  });

  const rows = uploadsQuery.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Upload History</h2>
        <p className="text-sm text-muted-foreground">Audit log of uploaded files from the backend upload APIs.</p>
      </div>

      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs">Report Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{REPORT_TYPES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{STATUSES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {uploadsQuery.isLoading ? (
        <div className="text-sm text-muted-foreground">Loading upload history...</div>
      ) : uploadsQuery.error ? (
        <div className="text-sm text-destructive">Unable to load upload history.</div>
      ) : (
        <DataTable
          columns={[
            { key: "id", header: "Upload ID", render: (row: UploadHistory) => row.id.slice(0, 8) },
            { key: "original_file_name", header: "File Name" },
            { key: "report_type", header: "Report Type" },
            { key: "uploaded_by", header: "Uploaded By" },
            { key: "uploaded_at", header: "Upload Date", render: (row: UploadHistory) => new Date(row.uploaded_at).toLocaleString() },
            { key: "total_records", header: "Records", align: "right", render: (row: UploadHistory) => row.total_records.toLocaleString() },
            {
              key: "upload_status",
              header: "Status",
              render: (row: UploadHistory) => (
                <Badge variant="secondary" className={statusColor[row.upload_status] ?? ""}>{row.upload_status}</Badge>
              ),
            },
            {
              key: "actions",
              header: "",
              align: "right",
              render: (row: UploadHistory) => (
                <div className="flex gap-1 justify-end">
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
                  {canWrite && (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="text-destructive"
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(row.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          data={rows}
          rowKey={(row) => row.id}
        />
      )}
      {importMutation.error && <p className="text-sm text-destructive">Unable to import master database upload.</p>}
      {deleteMutation.error && <p className="text-sm text-destructive">Unable to delete upload.</p>}
    </div>
  );
}
