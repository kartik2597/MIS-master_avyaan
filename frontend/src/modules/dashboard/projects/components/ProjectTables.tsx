import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Pager } from "@/shared/components/Pager/Pager";
import { EMPTY_TEAM, type TeamFilters } from "@/shared/components/Filters/DashboardFilters";
import { getErrorMessage } from "@/lib/api-client";
import { getProjectBench, getProjectEmployees } from "@/services/api/projects";
import type { ProjectHoursRow } from "@/services/api/types";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";

const PAGE_SIZE = 10;
const SEARCH_DELAY_MS = 300;

interface TableProps {
  from: string;
  to: string;
  /** Process / manager / TL / employee filters from the dashboard. */
  team?: TeamFilters;
  disabled?: boolean;
}

function hours(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function teamParams(team: TeamFilters) {
  return {
    process: team.process || undefined,
    manager: team.manager || undefined,
    tl: team.tl || undefined,
    emp_id: team.emp_id.trim() || undefined,
  };
}

function TableSkeleton({ label }: { label: string }) {
  return (
    <div className="space-y-2" role="status" aria-label={label}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  );
}

interface ProjectsTableProps {
  items: ProjectHoursRow[];
  loading?: boolean;
  error?: string;
}

/** Hours per project, with the client and how many people worked on it. */
export function ProjectsTable({ items, loading, error }: ProjectsTableProps) {
  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="space-y-0.5">
        <h3 className="text-sm font-semibold text-foreground">Projects</h3>
        <p className="text-xs text-muted-foreground">Hours logged on each project in the period.</p>
      </div>
      {loading ? (
        <TableSkeleton label="Loading projects" />
      ) : error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No project hours for this period.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project</TableHead>
              <TableHead>Client</TableHead>
              <TableHead className="text-right">People</TableHead>
              <TableHead className="text-right">Billable hrs</TableHead>
              <TableHead className="text-right">Total hrs</TableHead>
              <TableHead className="text-right">Share</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((row) => (
              <TableRow key={row.project_name}>
                <TableCell className="font-medium text-foreground">{row.project_name}</TableCell>
                <TableCell className="text-muted-foreground">{row.client_name}</TableCell>
                <TableCell className="text-right tabular-nums">{row.employees}</TableCell>
                <TableCell className="text-right tabular-nums">{hours(row.billable_hours)}</TableCell>
                <TableCell className="text-right tabular-nums">{hours(row.total_hours)}</TableCell>
                <TableCell className="text-right tabular-nums">{row.share_percent.toFixed(1)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Card>
  );
}

/** One row per employee: hours, billable share, projects worked on and days logged. */
export function EmployeeHoursTable({ from, to, team = EMPTY_TEAM, disabled }: TableProps) {
  const [searchText, setSearchText] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchText.trim());
      setPage(1);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchText]);

  useEffect(() => {
    setPage(1);
  }, [from, to, team.process, team.manager, team.tl, team.emp_id]);

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["dashboard", "projects", "employees", from, to, team, search, page],
    queryFn: () =>
      getProjectEmployees({
        date_from: from || undefined,
        date_to: to || undefined,
        ...teamParams(team),
        search: search || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: !disabled,
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const items = data?.items ?? [];

  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-0.5">
          <h3 className="text-sm font-semibold text-foreground">Employee hours</h3>
          <p className="text-xs text-muted-foreground">
            {total.toLocaleString()} {total === 1 ? "employee" : "employees"}
            {search ? ` matching "${search}"` : ""}. Most hours first.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by name or employee ID"
            aria-label="Search employees"
            className="pl-8"
          />
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton label="Loading employee hours" />
      ) : error ? (
        <p className="text-sm text-destructive">{getErrorMessage(error, "Unable to load employee hours.")}</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          {search ? "No employees match your search." : "No employee hours for this period."}
        </p>
      ) : (
        <div className={cn("transition-opacity", isFetching && "opacity-60")} aria-busy={isFetching}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead className="text-right">Projects</TableHead>
                <TableHead className="text-right">Days</TableHead>
                <TableHead className="text-right">Billable hrs</TableHead>
                <TableHead className="text-right">Total hrs</TableHead>
                <TableHead className="text-right">Billable %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((row) => (
                <TableRow key={row.emp_id}>
                  <TableCell>
                    <p className="font-medium text-foreground">{row.employee_name}</p>
                    <p className="text-xs text-muted-foreground">{row.emp_id}</p>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{row.projects}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.days_logged}</TableCell>
                  <TableCell className="text-right tabular-nums">{hours(row.billable_hours)}</TableCell>
                  <TableCell className="text-right tabular-nums">{hours(row.total_hours)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {row.billable_percent === null ? "—" : `${row.billable_percent.toFixed(0)}%`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Pager page={page} pageSize={PAGE_SIZE} total={total} busy={isFetching} onPageChange={setPage} />
    </Card>
  );
}

/** Active employees who logged no project hours in the period. */
export function BenchTable({ from, to, team = EMPTY_TEAM, disabled }: TableProps) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [from, to, team.process, team.manager, team.tl, team.emp_id]);

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["dashboard", "projects", "bench", from, to, team, page],
    queryFn: () =>
      getProjectBench({
        date_from: from || undefined,
        date_to: to || undefined,
        ...teamParams(team),
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: !disabled,
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const items = data?.items ?? [];

  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="space-y-0.5">
        <h3 className="text-sm font-semibold text-foreground">Bench</h3>
        <p className="text-xs text-muted-foreground">
          {total.toLocaleString()} active {total === 1 ? "employee" : "employees"} with no project hours in the
          period.
        </p>
      </div>

      {isLoading ? (
        <TableSkeleton label="Loading bench" />
      ) : error ? (
        <p className="text-sm text-destructive">{getErrorMessage(error, "Unable to load the bench list.")}</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          Nobody is on the bench. This list stays empty when no timesheet has been uploaded for the period.
        </p>
      ) : (
        <div className={cn("transition-opacity", isFetching && "opacity-60")} aria-busy={isFetching}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Process</TableHead>
                <TableHead>Designation</TableHead>
                <TableHead>Manager</TableHead>
                <TableHead>Team lead</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((row) => (
                <TableRow key={row.emp_id}>
                  <TableCell>
                    <p className="font-medium text-foreground">{row.employee_name}</p>
                    <p className="text-xs text-muted-foreground">{row.emp_id}</p>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{row.process}</TableCell>
                  <TableCell className="text-muted-foreground">{row.designation}</TableCell>
                  <TableCell className="text-muted-foreground">{row.manager_name || "—"}</TableCell>
                  <TableCell className="text-muted-foreground">{row.tl_name || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Pager page={page} pageSize={PAGE_SIZE} total={total} busy={isFetching} onPageChange={setPage} />
    </Card>
  );
}
