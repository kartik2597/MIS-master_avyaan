import { useState } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { KPICard, KPICardSkeleton } from "@/shared/components/KPICard/KPICard";
import { DashboardFilters, EMPTY_TEAM, type DateRange, type TeamFilters } from "@/shared/components/Filters/DashboardFilters";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/api-client";
import { getHiringSummary, getHiringTeams, getHiringTrends } from "@/services/api/hiring";
import { cn } from "@/lib/utils";
import { HiringTrendChart } from "../components/HiringCharts";
import { EventsTable, ExitReasons, TeamsTable } from "../components/HiringTables";
import { ArrowLeftRight, RefreshCw, TrendingDown, UserCheck, UserMinus, UserPlus, Users } from "lucide-react";

const GRID = "grid grid-cols-2 lg:grid-cols-3 gap-3";

export function HiringDashboard() {
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
    queryKey: ["dashboard", "hiring", "summary", range.from, range.to, team],
    queryFn: () => getHiringSummary(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });
  // The chart and tables load on their own, so a slow one never blocks the headline numbers.
  const trends = useQuery({
    queryKey: ["dashboard", "hiring", "trends", range.from, range.to, team],
    queryFn: () => getHiringTrends(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });
  const teams = useQuery({
    queryKey: ["dashboard", "hiring", "teams", range.from, range.to, team],
    queryFn: () => getHiringTeams(params),
    enabled: !rangeInvalid,
    placeholderData: keepPreviousData,
  });

  const data = summary.data;
  const period =
    data?.date_from && data?.date_to
      ? `Showing ${data.date_from} to ${data.date_to}${range.from || range.to ? "" : ", the latest 90 days with data"}.`
      : range.from || range.to
        ? `Showing ${range.from || "the start"} to ${range.to || "the latest date"}.`
        : "Showing the latest 90 days with data.";

  const header = (
    <PageHeader
      title="Hiring & Attrition"
      description={period}
      actions={
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["dashboard", "hiring"] })}
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
        <div className={GRID} role="status" aria-label="Loading hiring dashboard">
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
          title="Unable to load hiring dashboard"
          message={getErrorMessage(summary.error, "Unable to load hiring and attrition data.")}
        />
      </div>
    );
  }

  const noData = <span className="text-base text-muted-foreground">No data</span>;
  const show = (value: string | number) => (data.has_data ? value : noData);
  const headcount = (value: number | null) => show(value === null ? "—" : value);
  const trendError = trends.error ? getErrorMessage(trends.error, "Unable to load the monthly chart.") : undefined;
  const teamError = teams.error ? getErrorMessage(teams.error, "Unable to load teams.") : undefined;

  return (
    <div className="space-y-6">
      {header}
      {filters}

      {!data.has_data && (
        <div role="alert" className="rounded-md border border-warning/40 bg-warning/10 px-4 py-3 text-sm">
          No hiring or attrition report has been uploaded for this period. Upload a Hiring &amp; Attrition report on
          the Upload Reports page to see joiners, leavers and the attrition rate.
        </div>
      )}

      <div className={cn("space-y-6 transition-opacity", summary.isFetching && "opacity-60")} aria-busy={summary.isFetching}>
        <div className={GRID}>
          <KPICard label="Joiners" value={show(data.joiners)} icon={UserPlus} tone="success" />
          <KPICard label="Leavers" value={show(data.leavers)} icon={UserMinus} tone="destructive" />
          <KPICard
            label="Net Change"
            value={show(data.net_change > 0 ? `+${data.net_change}` : data.net_change)}
            icon={ArrowLeftRight}
            tone={data.net_change < 0 ? "warning" : "info"}
          />
          <KPICard
            label="Attrition"
            value={show(data.attrition_percent === null ? "—" : `${data.attrition_percent.toFixed(1)}%`)}
            icon={TrendingDown}
            tone="warning"
          />
          <KPICard label="Opening Headcount" value={headcount(data.opening_headcount)} icon={Users} tone="default" />
          <KPICard label="Closing Headcount" value={headcount(data.closing_headcount)} icon={UserCheck} tone="info" />
        </div>
        <p className="text-xs text-muted-foreground">
          Attrition is leavers as a share of the average of opening and closing headcount. Opening headcount counts
          employees in Employee Master who had joined before the period and had not left.
        </p>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <HiringTrendChart points={trends.data?.points ?? []} loading={trends.isLoading} error={trendError} />
          </div>
          <ExitReasons reasons={data.top_exit_reasons} />
        </div>

        <TeamsTable items={teams.data?.items ?? []} loading={teams.isLoading} error={teamError} />
        <EventsTable from={range.from} to={range.to} team={team} disabled={rangeInvalid} />
      </div>
    </div>
  );
}
