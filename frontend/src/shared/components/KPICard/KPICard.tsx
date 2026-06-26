import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

interface KPICardProps {
  label: string;
  value: ReactNode;
  delta?: number;
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

export function KPICard({ label, value, delta, suffix, icon: Icon, tone = "default" }: KPICardProps) {
  const trendIcon = delta == null ? Minus : delta > 0 ? ArrowUp : delta < 0 ? ArrowDown : Minus;
  const TrendIcon = trendIcon;
  const trendColor =
    delta == null ? "text-muted-foreground" : delta > 0 ? "text-success" : delta < 0 ? "text-destructive" : "text-muted-foreground";

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide truncate">{label}</p>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-semibold text-foreground tabular-nums">{value}</span>
            {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
          </div>
          {delta != null && (
            <div className={cn("flex items-center gap-1 text-xs font-medium", trendColor)}>
              <TrendIcon className="h-3 w-3" />
              <span>{Math.abs(delta)}% vs last period</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg shrink-0", toneMap[tone])}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </Card>
  );
}
