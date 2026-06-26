import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { uploadFile } from "@/services/api/uploads";
import type { FileUploadDetectionResponse } from "@/services/api/types";
import { AlertCircle, CheckCircle2, FileSpreadsheet, Loader2, Upload } from "lucide-react";

interface UploadResult {
  fileName: string;
  response?: FileUploadDetectionResponse;
  error?: string;
}

export function UploadsPage() {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<UploadResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (response) => {
      setResult({ fileName: response.file_name, response });
      queryClient.invalidateQueries({ queryKey: ["uploads"] });
    },
    onError: (error, file) => {
      setResult({ fileName: file.name, error: error instanceof Error ? error.message : "Upload failed" });
    },
  });

  function submitFile(file: File | undefined) {
    if (!file) return;
    setResult({ fileName: file.name });
    uploadMutation.mutate(file);
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Upload Reports</h2>
        <p className="text-sm text-muted-foreground">Drop one MIS report file. Supported formats are XLSX, XLS and CSV.</p>
      </div>

      <Card className="p-6">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            submitFile(e.dataTransfer.files.item(0) ?? undefined);
          }}
          className={`border-2 border-dashed rounded-lg py-12 text-center transition-colors cursor-pointer ${
            dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30"
          }`}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => submitFile(e.target.files?.item(0) ?? undefined)}
          />
          <div className="flex flex-col items-center gap-3">
            <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
              <Upload className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="font-medium">Drag and drop a file here</p>
              <p className="text-sm text-muted-foreground">or click to browse</p>
            </div>
            <Button
              type="button"
              variant="outline"
              disabled={uploadMutation.isPending}
              onClick={(e) => {
                e.stopPropagation();
                inputRef.current?.click();
              }}
            >
              Browse files
            </Button>
          </div>
        </div>
      </Card>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Upload Result</h3>
        {!result ? (
          <Card className="p-10 text-center text-muted-foreground text-sm">No file uploaded in this session.</Card>
        ) : (
          <Card className="p-4 flex items-center gap-4 flex-wrap">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-[220px]">
              <p className="font-medium text-sm truncate">{result.fileName}</p>
              {result.response && (
                <p className="text-xs text-muted-foreground">
                  {result.response.detected_report_type ?? "Unknown report"} with {result.response.confidence_score}% confidence
                </p>
              )}
              {result.error && <p className="text-xs text-destructive">{result.error}</p>}
            </div>
            {uploadMutation.isPending ? (
              <Badge variant="secondary" className="gap-1">
                <Loader2 className="h-3 w-3 animate-spin" /> Uploading
              </Badge>
            ) : result.error ? (
              <Badge variant="secondary" className="bg-destructive/15 text-destructive gap-1">
                <AlertCircle className="h-3 w-3" /> Failed
              </Badge>
            ) : (
              <Badge variant="secondary" className="bg-success/15 text-success gap-1">
                <CheckCircle2 className="h-3 w-3" /> Uploaded
              </Badge>
            )}
            {result.response && result.response.missing_columns.length > 0 && (
              <div className="w-full text-xs text-destructive">
                Missing columns: {result.response.missing_columns.join(", ")}
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
