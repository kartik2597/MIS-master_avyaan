import { useState, type ComponentType } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { KPICard, KPICardSkeleton } from "@/shared/components/KPICard/KPICard";
import { DashboardFilters, EMPTY_TEAM, type DateRange, type TeamFilters } from "@/shared/components/Filters/DashboardFilters";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/api-client";
import { getDashboardAttendance, getDashboardKpis, getDashboardTrends } from "@/services/api/dashboard";
import { cn } from "@/lib/utils";
import { AgentTable } from "../components/AgentTable";
import { AttendanceBreakdown } from "../components/AttendanceBreakdown";
import { PeopleTrendChart, RateTrendChart, TimeTrendChart } from "../components/TrendCharts";
import {
  Activity,
  AlertTriangle,
  ChevronDown,
  Clock,
  Coffee,
  LogOut,
  RefreshCw,
  Target,
  Timer,
  TrendingDown,
  UserCheck,
  Users,
} from "lucide-react";

type Tone = "default" | "success" | "warning" | "info" | "destructive";

interface KpiItem {
  label: string;
  value: number | string;
  icon: ComponentType<{ className?: string }>;
  tone: Tone;
  suffix?: string;
  /** The uploaded report this card is calculated from. No rows for it means "No data", not 0. */
  report: "APR" | "SHIFT_ADHERENCE" | "SHRINKAGE";
}

interface KpiSection {
  title: string;
  items: KpiItem[];
}

function numeric(value: number | string) {
  return Number(value ?? 0);
}

function formatNumber(value: number | string) {
  return numeric(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function percentOf(part: number, whole: number) {
  return whole > 0 ? (part / whole) * 100 : null;
}

const HEADLINE_GRID = "grid grid-cols-2 lg:grid-cols-4 gap-3";
const GRID = "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3";

const REPORT_NAMES: Record<string, string> = {
  APR: "APR",
  SHIFT_ADHERENCE: "Shift Adherence",
  SHRINKAGE: "Shrinkage",
};

export function AgentDashboard() {
  const queryClient = useQueryClient();
  const [range, setRange] = useState<DateRange>({ from: "", to: "" });
  const [team, setTeam] = useState<TeamFilters>(EMPTY_TEAM);
  const [showAllMetrics, setShowAllMetrics] = useState(false);
  const rangeInvalid = Boolean(range.from && range.to && range.from > range.to);
  const params = {
    date_from: range.from || undefined,
    date_to: range.to || undefined,
    process: team.process || undefined,
    manager: team.manager || undefined,
    tl: team.tl || undefined,
    emp_id: team.emp_id.trim() || undefined,
  };

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["dashboard", "kpis", range.from, range.to, team],
    queryFn: () => getDashboardKpis(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });

  // The charts load on their own, so a slow chart never blocks the headline numbers.
  const trends = useQuery({
    queryKey: ["dashboard", "trends", range.from, range.to, team],
    queryFn: () => getDashboardTrends(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });
  const attendance = useQuery({
    queryKey: ["dashboard", "attendance", range.from, range.to, team],
    queryFn: () => getDashboardAttendance(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });

  const header = (
    <PageHeader
      title="Agent Dashboard"
      description={
        range.from || range.to
          ? `Showing ${range.from || "the start"} to ${range.to || "the latest date"}.`
          : data?.report_date
            ? `Showing ${data.report_date}, the latest day with data.`
            : "Showing the latest day with data."
      }
      actions={
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["dashboard"] })}
          disabled={isFetching}
        >
          <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", isFetching && "animate-spin")} /> Refresh
        </Button>
      }
    />
  );
  const filters = (
    <DashboardFilters value={range} onChange={setRange} team={team} onTeamChange={setTeam} />
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        {header}
        {filters}
        <div className={HEADLINE_GRID} role="status" aria-label="Loading dashboard">
          {Array.from({ length: 4 }).map((_, i) => (
            <KPICardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        {header}
        {filters}
        <ErrorState title="Unable to load dashboard" message={getErrorMessage(error, "Unable to load dashboard KPIs.")} />
      </div>
    );
  }

  const presentPercent = percentOf(data.present_count, data.head_count);
  const adherencePercent = percentOf(
    data.shift_adherence_count,
    data.shift_adherence_count + data.non_adherence_count,
  );

  const headline: KpiItem[] = [
    { label: "Head Count", value: data.head_count, icon: Users, tone: "info", report: "SHRINKAGE" },
    {
      label: "Present",
      value: data.present_count,
      suffix: presentPercent === null ? undefined : `${presentPercent.toFixed(0)}%`,
      icon: UserCheck,
      tone: "success",
      report: "SHRINKAGE",
    },
    {
      label: "Shift Adherence",
      value: adherencePercent === null ? "—" : `${adherencePercent.toFixed(1)}%`,
      icon: Target,
      tone: "success",
      report: "SHIFT_ADHERENCE",
    },
    {
      label: "Overall Shrinkage",
      value: `${formatNumber(data.overall_shrinkage)}%`,
      icon: TrendingDown,
      tone: "warning",
      report: "SHRINKAGE",
    },
  ];

  const sections: KpiSection[] = [
    {
      title: "Workforce",
      items: [
        { label: "Attrition", value: data.attrition_count, icon: TrendingDown, tone: "destructive", report: "SHRINKAGE" },
      ],
    },
    {
      title: "Attendance & adherence",
      items: [
        { label: "Late Login", value: data.late_login_count, icon: Clock, tone: "warning", report: "SHIFT_ADHERENCE" },
        { label: "Early Logout", value: data.early_logout_count, icon: LogOut, tone: "warning", report: "SHIFT_ADHERENCE" },
        { label: "Shift Adherence (count)", value: data.shift_adherence_count, icon: Target, tone: "success", report: "SHIFT_ADHERENCE" },
        { label: "Non Adherence", value: data.non_adherence_count, icon: AlertTriangle, tone: "destructive", report: "SHIFT_ADHERENCE" },
      ],
    },
    {
      title: "Shrinkage",
      items: [
        { label: "Planned Shrinkage (%)", value: formatNumber(data.planned_shrinkage), icon: TrendingDown, tone: "info", report: "SHRINKAGE" },
        { label: "Unplanned Shrinkage (%)", value: formatNumber(data.unplanned_shrinkage), icon: TrendingDown, tone: "destructive", report: "SHRINKAGE" },
      ],
    },
    {
      title: "Time utilisation (hrs)",
      items: [
        { label: "Talk Time", value: formatNumber(data.total_talk_time), icon: Timer, tone: "info", report: "APR" },
        { label: "Login Hours", value: formatNumber(data.total_login_time), icon: Activity, tone: "info", report: "SHIFT_ADHERENCE" },
        { label: "Staff Time", value: formatNumber(data.total_staff_time), icon: Timer, tone: "default", report: "APR" },
        { label: "Downtime", value: formatNumber(data.total_downtime), icon: AlertTriangle, tone: "destructive", report: "SHIFT_ADHERENCE" },
        { label: "Idle Time", value: formatNumber(data.total_idle_time), icon: Coffee, tone: "warning", report: "APR" },
        { label: "Break Time", value: formatNumber(data.total_break_time), icon: Coffee, tone: "warning", report: "APR" },
      ],
    },
  ];

  const missingReports = data.missing_reports ?? [];

  function renderCard(item: KpiItem) {
    const { report, ...card } = item;
    return (
      <KPICard
        key={item.label}
        {...card}
        suffix={missingReports.includes(report) ? undefined : card.suffix}
        value={
          missingReports.includes(report) ? (
            <span className="text-base text-muted-foreground">No data</span>
          ) : (
            card.value
          )
        }
      />
    );
  }

  const points = trends.data?.points ?? [];
  const trendError = trends.error ? getErrorMessage(trends.error, "Unable to load trends.") : undefined;
  const attendanceError = attendance.error
    ? getErrorMessage(attendance.error, "Unable to load attendance.")
    : undefined;

  return (
    <div className="space-y-6">
      {header}
      {filters}

      {missingReports.length > 0 && (
        <div role="alert" className="rounded-md border border-warning/40 bg-warning/10 px-4 py-3 text-sm">
          No data uploaded for this period for: {missingReports.map((r) => REPORT_NAMES[r] ?? r).join(", ")}.
          Cards that depend on these reports show &quot;No data&quot; instead of 0.
        </div>
      )}

      <div className={cn("space-y-6 transition-opacity", isFetching && "opacity-60")} aria-busy={isFetching}>
        <div className={HEADLINE_GRID}>{headline.map(renderCard)}</div>

        <div className="grid gap-4 lg:grid-cols-3">
          <AttendanceBreakdown data={attendance.data} loading={attendance.isLoading} error={attendanceError} />
          <div className="lg:col-span-2">
            <PeopleTrendChart points={points} loading={trends.isLoading} error={trendError} />
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <RateTrendChart points={points} loading={trends.isLoading} error={trendError} />
          <TimeTrendChart points={points} loading={trends.isLoading} error={trendError} />
        </div>

        <AgentTable from={range.from} to={range.to} team={team} disabled={rangeInvalid} />

        <section className="space-y-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowAllMetrics((open) => !open)}
            aria-expanded={showAllMetrics}
            className="-ml-2 text-muted-foreground"
          >
            <ChevronDown className={cn("h-4 w-4 mr-1.5 transition-transform", showAllMetrics && "rotate-180")} />
            {showAllMetrics ? "Hide all metrics" : "Show all metrics"}
          </Button>
          {showAllMetrics && (
            <div className="space-y-6">
              {sections.map((section) => (
                <div key={section.title} className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {section.title}
                  </h3>
                  <div className={GRID}>{section.items.map(renderCard)}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
