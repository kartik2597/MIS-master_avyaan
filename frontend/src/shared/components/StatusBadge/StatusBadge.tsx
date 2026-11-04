import { cn } from "@/lib/utils";

type Tone = "success" | "info" | "warning" | "destructive" | "neutral";

const toneClass: Record<Tone, string> = {
  success: "bg-success/15 text-success",
  info: "bg-info/15 text-info",
  warning: "bg-warning/20 text-warning-foreground",
  destructive: "bg-destructive/10 text-destructive",
  neutral: "bg-muted text-muted-foreground",
};

const dotClass: Record<Tone, string> = {
  success: "bg-success",
  info: "bg-info",
  warning: "bg-warning",
  destructive: "bg-destructive",
  neutral: "bg-muted-foreground/60",
};

const UPLOAD_STATUS_TONE: Record<string, Tone> = {
  COMPLETED: "success",
  VALIDATED: "info",
  PROCESSING: "warning",
  PENDING: "neutral",
  FAILED: "destructive",
  VALIDATION_FAILED: "destructive",
};

/** Turns "VALIDATION_FAILED" into "Validation failed". */
export function humanize(value: string) {
  const text = value.replaceAll("_", " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

interface StatusBadgeProps {
  label: string;
  tone?: Tone;
  className?: string;
}

export function StatusBadge({ label, tone = "neutral", className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        toneClass[tone],
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClass[tone], tone === "warning" && "animate-pulse")} />
      {label}
    </span>
  );
}

export function UploadStatusBadge({ status }: { status: string }) {
  return <StatusBadge label={humanize(status)} tone={UPLOAD_STATUS_TONE[status] ?? "neutral"} />;
}
