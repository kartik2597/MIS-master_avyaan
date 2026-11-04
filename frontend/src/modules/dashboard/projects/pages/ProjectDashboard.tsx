import { useState } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { KPICard, KPICardSkeleton } from "@/shared/components/KPICard/KPICard";
import { DashboardFilters, EMPTY_TEAM, type DateRange, type TeamFilters } from "@/shared/components/Filters/DashboardFilters";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/api-client";
import { getProjectHours, getProjectSummary, getProjectTrends } from "@/services/api/projects";
import { cn } from "@/lib/utils";
import { HoursByProjectChart, HoursTrendChart } from "../components/ProjectCharts";
import { BenchTable, EmployeeHoursTable, ProjectsTable } from "../components/ProjectTables";
import { BadgeCheck, Briefcase, Clock, FolderKanban, RefreshCw, Timer, Users } from "lucide-react";

const GRID = "grid grid-cols-2 lg:grid-cols-3 gap-3";

function formatHours(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function ProjectDashboard() {
  const queryClient = useQueryClient();
  const [range, setRange] = useState<DateRange>({ from: "", to: "" });
  const [team, setTeam] = useState<TeamFilters>(EMPTY_TEAM);
  const rangeInvalid = Boolean(range.from && range.to && range.from > range.to);
  const params = {
    date_from: range.from || undefined,
    date_to: range.to || undefined,
    process: team.process || undefined,
    manager: team.manager || undefined,
    tl: team.tl || undefined,
    emp_id: team.emp_id.trim() || undefined,
  };

  const summary = useQuery({
    queryKey: ["dashboard", "projects", "summary", range.from, range.to, team],
    queryFn: () => getProjectSummary(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });
  // The charts and tables load on their own, so a slow one never blocks the headline numbers.
  const trends = useQuery({
    queryKey: ["dashboard", "projects", "trends", range.from, range.to, team],
    queryFn: () => getProjectTrends(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });
  const projects = useQuery({
    queryKey: ["dashboard", "projects", "by-project", range.from, range.to, team],
    queryFn: () => getProjectHours(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });

  const data = summary.data;
  const period =
    data?.date_from && data?.date_to
      ? `Showing ${data.date_from} to ${data.date_to}${range.from || range.to ? "" : ", the latest 30 days with data"}.`
      : range.from || range.to
        ? `Showing ${range.from || "the start"} to ${range.to || "the latest date"}.`
        : "Showing the latest 30 days with data.";

  const header = (
    <PageHeader
      title="Project & Timesheet"
      description={period}
      actions={
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["dashboard", "projects"] })}
          disabled={summary.isFetching}
        >
          <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", summary.isFetching && "animate-spin")} /> Refresh
        </Button>
      }
    />
  );
  const filters = (
    <DashboardFilters value={range} onChange={setRange} team={team} onTeamChange={setTeam} />
  );

  if (summary.isLoading) {
    return (
      <div className="space-y-6">
        {header}
        {filters}
        <div className={GRID} role="status" aria-label="Loading project dashboard">
          {Array.from({ length: 6 }).map((_, i) => (
            <KPICardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (summary.error || !data) {
    return (
      <div className="space-y-6">
        {header}
        {filters}
        <ErrorState
          title="Unable to load project dashboard"
          message={getErrorMessage(summary.error, "Unable to load project hours.")}
        />
      </div>
    );
  }

  const noData = <span className="text-base text-muted-foreground">No data</span>;
  const show = (value: string | number) => (data.has_data ? value : noData);
  const trendError = trends.error ? getErrorMessage(trends.error, "Unable to load hours per day.") : undefined;
  const projectError = projects.error ? getErrorMessage(projects.error, "Unable to load projects.") : undefined;
  const projectItems = projects.data?.items ?? [];

  return (
    <div className="space-y-6">
      {header}
      {filters}

      {!data.has_data && (
        <div role="alert" className="rounded-md border border-warning/40 bg-warning/10 px-4 py-3 text-sm">
          No project timesheet has been uploaded for this period. Upload a Project Timesheet report on the Upload
          Reports page to see hours, projects and the bench list.
        </div>
      )}

      <div className={cn("space-y-6 transition-opacity", summary.isFetching && "opacity-60")} aria-busy={summary.isFetching}>
        <div className={GRID}>
          <KPICard label="Total Hours" value={show(formatHours(data.total_hours))} icon={Clock} tone="info" />
          <KPICard
            label="Billable Hours"
            value={show(formatHours(data.billable_hours))}
            icon={BadgeCheck}
            tone="success"
          />
          <KPICard
            label="Billable Share"
            value={show(data.billable_percent === null ? "—" : `${data.billable_percent.toFixed(1)}%`)}
            icon={Timer}
            tone="success"
          />
          <KPICard label="Employees Logged" value={show(data.employees_logged)} icon={Users} tone="default" />
          <KPICard label="Active Projects" value={show(data.active_projects)} icon={FolderKanban} tone="info" />
          <KPICard
            label="Avg Hours / Employee"
            value={show(formatHours(data.avg_hours_per_employee))}
            icon={Briefcase}
            tone="warning"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <HoursTrendChart points={trends.data?.points ?? []} loading={trends.isLoading} error={trendError} />
          <HoursByProjectChart items={projectItems} loading={projects.isLoading} error={projectError} />
        </div>

        <ProjectsTable items={projectItems} loading={projects.isLoading} error={projectError} />
        <EmployeeHoursTable from={range.from} to={range.to} team={team} disabled={rangeInvalid} />
        <BenchTable from={range.from} to={range.to} team={team} disabled={rangeInvalid} />
      </div>
    </div>
  );
}
