import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { StatusBadge, humanize } from "@/shared/components/StatusBadge/StatusBadge";
import { uploadFile } from "@/services/api/uploads";
import { getErrorMessage } from "@/lib/api-client";
import { IMPORT_ORDER, IMPORTABLE_REPORT_TYPES, importReport } from "@/services/api/imports";
import type { FileUploadDetectionResponse, ImportSummary, SheetUploadResult } from "@/services/api/types";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, FileSpreadsheet, History, Loader2, Upload } from "lucide-react";

interface UploadResult {
  fileName: string;
  response?: FileUploadDetectionResponse;
  error?: string;
}

interface ImportState {
  summary?: ImportSummary;
  error?: string;
}

const FORMATS = ["XLSX", "XLS", "CSV"];

const STEPS = [
  { title: "Upload", text: "Drop an XLSX, XLS or CSV file. Every sheet is checked and its report type detected." },
  { title: "Review", text: "Check the detected report type and make sure no columns are missing." },
  {
    title: "Process",
    text: "Import the validated rows. They then appear on the dashboard and in Employee Master.",
  },
];

/** Every report found in the file. Older responses carry just the first one. */
function sheetsOf(response: FileUploadDetectionResponse): SheetUploadResult[] {
  if (response.sheets && response.sheets.length > 0) return response.sheets;
  return [
    {
      upload_id: response.upload_id,
      sheet_name: null,
      detected_report_type: response.detected_report_type,
      confidence_score: response.confidence_score,
      total_columns: response.total_columns,
      total_records: 0,
      missing_columns: response.missing_columns,
    },
  ];
}

function isProcessable(sheet: SheetUploadResult) {
  return (
    Boolean(sheet.detected_report_type) &&
    sheet.missing_columns.length === 0 &&
    IMPORTABLE_REPORT_TYPES.includes(sheet.detected_report_type!)
  );
}

export function UploadsPage() {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<UploadResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const [imports, setImports] = useState<Record<string, ImportState>>({});
  const [runningIds, setRunningIds] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (response) => {
      setResult({ fileName: response.file_name, response });
      queryClient.invalidateQueries({ queryKey: ["uploads"] });
    },
    onError: (error, file) => {
      setResult({ fileName: file.name, error: getErrorMessage(error, "Upload failed") });
    },
  });

  function submitFile(file: File | undefined) {
    if (!file) return;
    setImports({});
    // Dropped files skip the picker's `accept` filter, so check here too.
    if (!/\.(xlsx|xls|csv)$/i.test(file.name)) {
      setResult({ fileName: file.name, error: "Unsupported file type. Use XLSX, XLS or CSV." });
      return;
    }
    setResult({ fileName: file.name });
    uploadMutation.mutate(file);
  }

  async function processSheet(sheet: SheetUploadResult) {
    if (!sheet.detected_report_type) return;
    setRunningIds((ids) => [...ids, sheet.upload_id]);
    setImports((state) => ({ ...state, [sheet.upload_id]: {} }));
    try {
      const summary = await importReport(sheet.detected_report_type, sheet.upload_id);
      setImports((state) => ({ ...state, [sheet.upload_id]: { summary } }));
    } catch (error) {
      setImports((state) => ({
        ...state,
        [sheet.upload_id]: { error: getErrorMessage(error, "Processing failed") },
      }));
    } finally {
      setRunningIds((ids) => ids.filter((id) => id !== sheet.upload_id));
      queryClient.invalidateQueries({ queryKey: ["uploads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    }
  }

  async function processAll(sheets: SheetUploadResult[]) {
    const rank = (sheet: SheetUploadResult) => {
      const index = IMPORT_ORDER.indexOf(sheet.detected_report_type ?? "");
      return index === -1 ? IMPORT_ORDER.length : index;
    };
    const pending = sheets
      .filter((sheet) => isProcessable(sheet) && !imports[sheet.upload_id]?.summary)
      .sort((a, b) => rank(a) - rank(b));
    // One at a time: later reports (shrinkage) read what earlier ones (roster, activity) saved.
    for (const sheet of pending) {
      await processSheet(sheet);
    }
  }

  const uploading = uploadMutation.isPending;
  const sheets = result?.response ? sheetsOf(result.response) : [];
  const ignoredSheets = result?.response?.ignored_sheets ?? [];
  const processableCount = sheets.filter((sheet) => isProcessable(sheet) && !imports[sheet.upload_id]?.summary).length;
  const busy = runningIds.length > 0;

  function openPicker() {
    if (!uploading) inputRef.current?.click();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Upload Reports"
        description="Drop one MIS report file. Every sheet is checked: the report type is detected and the columns are validated automatically."
      />

      <Card className="p-6 shadow-card">
        <div
          role="button"
          tabIndex={0}
          aria-label="Upload a report file"
          aria-disabled={uploading}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (!uploading) submitFile(e.dataTransfer.files.item(0) ?? undefined);
          }}
          onClick={openPicker}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              openPicker();
            }
          }}
          className={cn(
            "border-2 border-dashed rounded-xl py-14 px-4 text-center transition-colors cursor-pointer",
            dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30",
            uploading && "cursor-progress opacity-70",
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => {
              submitFile(e.target.files?.item(0) ?? undefined);
              e.target.value = ""; // allow re-selecting the same file
            }}
          />
          <div className="flex flex-col items-center gap-4">
            <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
              {uploading ? (
                <Loader2 className="h-6 w-6 text-primary animate-spin" />
              ) : (
                <Upload className="h-6 w-6 text-primary" />
              )}
            </div>
            <div className="space-y-1">
              <p className="font-medium">{uploading ? "Uploading and checking your file..." : "Drag and drop a file here"}</p>
              <p className="text-sm text-muted-foreground">
                {uploading ? "This usually takes a few seconds." : "or click to browse your computer"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {FORMATS.map((f) => (
                <span key={f} className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {f}
                </span>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Upload result</h3>
          {processableCount > 1 && (
            <Button type="button" size="sm" onClick={() => processAll(sheets)} disabled={busy}>
              {busy ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> Processing
                </>
              ) : (
                `Process all ${processableCount} reports`
              )}
            </Button>
          )}
        </div>

        {!result ? (
          <Card className="shadow-card flex flex-col items-center gap-2 py-10 px-4 text-center">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-muted">
              <FileSpreadsheet className="h-5 w-5 text-muted-foreground" />
            </div>
            <p className="text-sm font-medium">No file uploaded in this session</p>
            <p className="text-sm text-muted-foreground">Your latest upload and its validation result will appear here.</p>
          </Card>
        ) : !result.response ? (
          <Card className="p-4 shadow-card flex items-center gap-4 flex-wrap">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-[220px]">
              <p className="font-medium text-sm truncate">{result.fileName}</p>
              {result.error && <p className="text-xs text-destructive">{result.error}</p>}
            </div>
            {uploading ? (
              <StatusBadge label="Uploading" tone="warning" />
            ) : (
              <StatusBadge label="Failed" tone="destructive" />
            )}
          </Card>
        ) : (
          <>
            {sheets.length > 1 && (
              <p className="text-sm text-muted-foreground">
                {result.fileName} contains {sheets.length} reports. Each one is validated and processed separately.
              </p>
            )}
            {sheets.map((sheet) => {
              const state = imports[sheet.upload_id] ?? {};
              const running = runningIds.includes(sheet.upload_id);
              const canProcess = isProcessable(sheet) && !state.summary;
              return (
                <Card key={sheet.upload_id} className="p-4 shadow-card flex items-center gap-4 flex-wrap">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <FileSpreadsheet className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <p className="font-medium text-sm truncate">
                      {sheet.sheet_name ? `${sheet.sheet_name} sheet` : result.fileName}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {sheet.detected_report_type ? humanize(sheet.detected_report_type) : "Unknown report"} detected
                      with {sheet.confidence_score}% confidence
                      {sheet.total_records > 0 ? ` · ${sheet.total_records.toLocaleString()} rows` : ""}
                    </p>
                  </div>
                  <StatusBadge label="Uploaded" tone="success" />

                  {sheet.missing_columns.length > 0 && (
                    <div className="w-full flex gap-2 rounded-lg bg-destructive/5 border border-destructive/20 p-3 text-sm text-destructive">
                      <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                      <p>
                        <span className="font-medium">Missing columns:</span> {sheet.missing_columns.join(", ")}
                      </p>
                    </div>
                  )}

                  {canProcess && (
                    <div className="w-full flex items-center gap-3 flex-wrap rounded-lg bg-muted/50 p-3">
                      <Button type="button" size="sm" onClick={() => processSheet(sheet)} disabled={busy}>
                        {running ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> Processing
                          </>
                        ) : (
                          "Process report"
                        )}
                      </Button>
                      <span className="text-xs text-muted-foreground">
                        Import the validated data so it appears on the dashboards.
                      </span>
                    </div>
                  )}

                  {state.summary && (
                    <div
                      className={cn(
                        "w-full flex gap-2 rounded-lg border p-3 text-sm",
                        state.summary.failed_records > 0
                          ? "bg-warning/10 border-warning/30 text-foreground"
                          : "bg-success/10 border-success/20 text-success",
                      )}
                    >
                      {state.summary.failed_records > 0 ? (
                        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-warning" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                      )}
                      <div className="space-y-1">
                        <p>
                          Processed {state.summary.processed_records.toLocaleString()} of{" "}
                          {state.summary.total_records.toLocaleString()} rows
                          {state.summary.failed_records > 0
                            ? ` (${state.summary.failed_records.toLocaleString()} failed)`
                            : ""}
                          .
                        </p>
                        {state.summary.failed_records > 0 && state.summary.message && (
                          <p className="text-xs text-muted-foreground break-words">{state.summary.message}</p>
                        )}
                      </div>
                    </div>
                  )}
                  {state.error && (
                    <div className="w-full flex gap-2 rounded-lg bg-destructive/5 border border-destructive/20 p-3 text-sm text-destructive">
                      <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                      <p>{state.error}</p>
                    </div>
                  )}
                </Card>
              );
            })}
            {ignoredSheets.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Skipped {ignoredSheets.length === 1 ? "sheet" : "sheets"} with no recognised report columns:{" "}
                {ignoredSheets.join(", ")}.
              </p>
            )}
          </>
        )}
      </section>

      <Card className="p-6 shadow-card space-y-5">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">How it works</h3>
          <Button asChild variant="ghost" size="sm">
            <Link to="/upload-history">
              <History className="h-3.5 w-3.5 mr-1.5" /> View upload history
            </Link>
          </Button>
        </div>
        <ol className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                {index + 1}
              </span>
              <div className="space-y-0.5">
                <p className="text-sm font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="space-y-2 border-t pt-4">
          <p className="text-xs text-muted-foreground">Reports that can be processed</p>
          <div className="flex flex-wrap gap-2">
            {IMPORTABLE_REPORT_TYPES.map((type) => (
              <span key={type} className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {humanize(type)}
              </span>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
