import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  description?: string;
  loading?: boolean;
  error?: string;
  /** True when the query worked but there is nothing to draw. */
  empty?: boolean;
  emptyText?: string;
  className?: string;
  children: ReactNode;
}

/** A titled card for one chart. Shows a skeleton, an error or an empty message instead of the chart. */
export function ChartCard({
  title,
  description,
  loading,
  error,
  empty,
  emptyText = "No data for this period.",
  className,
  children,
}: ChartCardProps) {
  let body: ReactNode = children;
  if (loading) {
    body = <Skeleton className="h-full w-full rounded-lg" />;
  } else if (error) {
    body = <p className="text-sm text-destructive text-center px-4">{error}</p>;
  } else if (empty) {
    body = <p className="text-sm text-muted-foreground text-center px-4">{emptyText}</p>;
  }

  const centered = Boolean(!loading && (error || empty));

  return (
    <Card className={cn("p-4 shadow-card", className)}>
      <div className="mb-3 space-y-0.5">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <div className={cn("h-64 w-full", centered && "flex items-center justify-center")}>{body}</div>
    </Card>
  );
}
