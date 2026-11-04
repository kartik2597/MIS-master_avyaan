import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/lib/api-client";
import { getUploadValidation } from "@/services/api/uploads";

interface UploadIssuesDialogProps {
  /** The upload to show. Null keeps the dialog closed. */
  uploadId: string | null;
  onClose: () => void;
}

/** Lists why an upload had problems: bad columns first, then each skipped row. */
export function UploadIssuesDialog({ uploadId, onClose }: UploadIssuesDialogProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["uploads", "validation", uploadId],
    queryFn: () => getUploadValidation(uploadId as string),
    enabled: Boolean(uploadId),
  });

  const hasColumnProblems = Boolean(data && (data.missing_columns.length || data.extra_columns.length));

  return (
    <Dialog open={Boolean(uploadId)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upload issues</DialogTitle>
          <DialogDescription>
            {data
              ? `${data.original_file_name}${data.sheet_name ? ` (${data.sheet_name})` : ""}`
              : "Loading details..."}
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-5/6" />
            <Skeleton className="h-6 w-2/3" />
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {getErrorMessage(error, "Unable to load the upload issues.")}
          </p>
        )}

        {data && (
          <div className="space-y-4 text-sm">
            <p className="text-muted-foreground">
              {data.processed_records.toLocaleString()} of {data.total_records.toLocaleString()} rows imported,{" "}
              {data.failed_records.toLocaleString()} skipped.
            </p>

            {data.error_message && data.row_errors.length === 0 && (
              <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2">
                {data.error_message}
              </p>
            )}

            {hasColumnProblems && (
              <section className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Columns</h3>
                {data.missing_columns.length > 0 && (
                  <p>
                    <span className="font-medium">Missing:</span> {data.missing_columns.join(", ")}
                  </p>
                )}
                {data.extra_columns.length > 0 && (
                  <p className="text-muted-foreground">
                    <span className="font-medium">Not used:</span> {data.extra_columns.join(", ")}
                  </p>
                )}
              </section>
            )}

            {data.row_errors.length > 0 && (
              <section className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Skipped rows
                </h3>
                <div className="max-h-72 overflow-y-auto rounded-md border">
                  <table className="w-full text-left">
                    <thead className="sticky top-0 bg-muted text-xs text-muted-foreground">
                      <tr>
                        <th className="w-20 px-3 py-2 font-medium">Row</th>
                        <th className="px-3 py-2 font-medium">Problem</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.row_errors.map((item, index) => (
                        <tr key={`${item.row}-${index}`} className="border-t align-top">
                          <td className="px-3 py-2 font-mono text-xs tabular-nums">
                            {item.row > 0 ? item.row : "File"}
                          </td>
                          <td className="px-3 py-2">{item.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {data.row_errors_truncated && (
                  <p className="text-xs text-muted-foreground">
                    Only the first {data.row_errors.length.toLocaleString()} problems are listed. Fix these and
                    re-upload to see the rest.
                  </p>
                )}
              </section>
            )}

            {!data.error_message && !hasColumnProblems && data.row_errors.length === 0 && (
              <p className="text-muted-foreground">No problems were recorded for this upload.</p>
            )}
          </div>
        )}

        <div className="flex justify-end">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
