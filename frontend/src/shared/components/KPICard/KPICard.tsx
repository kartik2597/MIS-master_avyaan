import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ComponentType, ReactNode } from "react";

interface KPICardProps {
  label: string;
  value: ReactNode;
  suffix?: string;
  icon?: ComponentType<{ className?: string }>;
  tone?: "default" | "success" | "warning" | "info" | "destructive";
}

const toneMap: Record<NonNullable<KPICardProps["tone"]>, string> = {
  default: "bg-primary/10 text-primary",
  success: "bg-success/15 text-success",
  warning: "bg-warning/20 text-warning-foreground",
  info: "bg-info/15 text-info",
  destructive: "bg-destructive/10 text-destructive",
};

const accentMap: Record<NonNullable<KPICardProps["tone"]>, string> = {
  default: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  info: "bg-info",
  destructive: "bg-destructive",
};

export function KPICard({ label, value, suffix, icon: Icon, tone = "default" }: KPICardProps) {
  return (
    <Card className="group relative overflow-hidden p-4 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-card-hover">
      <span className={cn("absolute inset-y-0 left-0 w-1 opacity-70 group-hover:opacity-100", accentMap[tone])} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <p className="text-xs font-medium text-muted-foreground leading-snug">{label}</p>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-semibold text-foreground tabular-nums tracking-tight">{value}</span>
            {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
          </div>
        </div>
        {Icon && (
          <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg shrink-0", toneMap[tone])}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
    </Card>
  );
}

export function KPICardSkeleton() {
  return (
    <Card className="p-4 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-3 flex-1">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-16" />
        </div>
        <Skeleton className="h-9 w-9 rounded-lg" />
      </div>
    </Card>
  );
}
