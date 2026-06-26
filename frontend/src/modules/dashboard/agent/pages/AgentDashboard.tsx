import { useQuery } from "@tanstack/react-query";
import { KPICard } from "@/shared/components/KPICard/KPICard";
import { getDashboardKpis } from "@/services/api/dashboard";
import {
  Activity,
  AlertTriangle,
  Clock,
  Coffee,
  LogOut,
  Target,
  Timer,
  TrendingDown,
  UserCheck,
  Users,
} from "lucide-react";

function numeric(value: number | string) {
  return Number(value ?? 0);
}

function formatNumber(value: number | string) {
  return numeric(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function AgentDashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", "kpis"],
    queryFn: getDashboardKpis,
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading dashboard KPIs...</div>;
  }

  if (error || !data) {
    return <div className="text-sm text-destructive">Unable to load dashboard KPIs.</div>;
  }

  const kpis = [
    { label: "Head Count", value: data.head_count, icon: Users, tone: "info" as const },
    { label: "Present Count", value: data.present_count, icon: UserCheck, tone: "success" as const },
    { label: "Late Login", value: data.late_login_count, icon: Clock, tone: "warning" as const },
    { label: "Early Logout", value: data.early_logout_count, icon: LogOut, tone: "warning" as const },
    { label: "Shift Adherence", value: data.shift_adherence_count, icon: Target, tone: "success" as const },
    { label: "Non Adherence", value: data.non_adherence_count, icon: AlertTriangle, tone: "destructive" as const },
    { label: "Planned Shrinkage", value: formatNumber(data.planned_shrinkage), icon: TrendingDown, tone: "info" as const },
    { label: "Unplanned Shrinkage", value: formatNumber(data.unplanned_shrinkage), icon: TrendingDown, tone: "destructive" as const },
    { label: "Overall Shrinkage", value: formatNumber(data.overall_shrinkage), icon: TrendingDown, tone: "warning" as const },
    { label: "Attrition", value: data.attrition_count, icon: TrendingDown, tone: "destructive" as const },
    { label: "Talk Time", value: formatNumber(data.total_talk_time), icon: Timer, tone: "info" as const },
    { label: "Login Hours", value: formatNumber(data.total_login_time), icon: Activity, tone: "info" as const },
    { label: "Total Login", value: formatNumber(data.total_login_time), icon: Activity, tone: "default" as const },
    { label: "Staff Time", value: formatNumber(data.total_staff_time), icon: Timer, tone: "default" as const },
    { label: "Downtime", value: formatNumber(data.total_downtime), icon: AlertTriangle, tone: "destructive" as const },
    { label: "Idle Time", value: formatNumber(data.total_idle_time), icon: Coffee, tone: "warning" as const },
    { label: "Break Time", value: formatNumber(data.total_break_time), icon: Coffee, tone: "warning" as const },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Agent Dashboard</h2>
        <p className="text-sm text-muted-foreground">Live KPI rollup from backend performance, adherence and shrinkage data.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
        {kpis.map((kpi) => <KPICard key={kpi.label} {...kpi} />)}
      </div>
    </div>
  );
}
