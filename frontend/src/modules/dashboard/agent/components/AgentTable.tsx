import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/shared/components/StatusBadge/StatusBadge";
import { getErrorMessage } from "@/lib/api-client";
import { getDashboardAgents } from "@/services/api/dashboard";
import { EMPTY_TEAM, type TeamFilters } from "@/shared/components/Filters/DashboardFilters";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

const PAGE_SIZE = 10;
const SEARCH_DELAY_MS = 300;

interface AgentTableProps {
  from: string;
  to: string;
  /** Process / manager / TL / employee filters from the dashboard. */
  team?: TeamFilters;
  disabled?: boolean;
}

function hours(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/** One row per agent for the chosen period, with search by name or employee id. */
export function AgentTable({ from, to, team = EMPTY_TEAM, disabled }: AgentTableProps) {
  const [searchText, setSearchText] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // Wait for a pause in typing before asking the server.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchText.trim());
      setPage(1);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchText]);

  // A new period or team filter starts again from the first page.
  useEffect(() => {
    setPage(1);
  }, [from, to, team.process, team.manager, team.tl, team.emp_id]);

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["dashboard", "agents", from, to, team, search, page],
    queryFn: () =>
      getDashboardAgents({
        date_from: from || undefined,
        date_to: to || undefined,
        process: team.process || undefined,
        manager: team.manager || undefined,
        tl: team.tl || undefined,
        emp_id: team.emp_id.trim() || undefined,
        search: search || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: !disabled,
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = data?.items ?? [];
  const singleDay = items.length > 0 && items.every((row) => row.days_recorded === 1);

  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-0.5">
          <h3 className="text-sm font-semibold text-foreground">Agents</h3>
          <p className="text-xs text-muted-foreground">
            {total.toLocaleString()} {total === 1 ? "agent" : "agents"}
            {search ? ` matching "${search}"` : ""}. Times are in hours.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by name or employee ID"
            aria-label="Search agents"
            className="pl-8"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2" role="status" aria-label="Loading agents">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-destructive">{getErrorMessage(error, "Unable to load agents.")}</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          {search ? "No agents match your search." : "No agent data for this period."}
        </p>
      ) : (
        <div className={cn("transition-opacity", isFetching && "opacity-60")} aria-busy={isFetching}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Process</TableHead>
                <TableHead>{singleDay ? "Attendance" : "Days present"}</TableHead>
                <TableHead className="text-right">Login</TableHead>
                <TableHead className="text-right">Talk</TableHead>
                <TableHead className="text-right">Idle</TableHead>
                <TableHead className="text-right">Break</TableHead>
                <TableHead className="text-right">Late</TableHead>
                <TableHead className="text-right">Early out</TableHead>
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
                  <TableCell>
                    {singleDay ? (
                      <StatusBadge
                        label={row.days_present > 0 ? "Present" : "Not present"}
                        tone={row.days_present > 0 ? "success" : "warning"}
                      />
                    ) : (
                      <span className="tabular-nums">
                        {row.days_present} / {row.days_recorded}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{hours(row.login_hours)}</TableCell>
                  <TableCell className="text-right tabular-nums">{hours(row.talk_time)}</TableCell>
                  <TableCell className="text-right tabular-nums">{hours(row.idle_time)}</TableCell>
                  <TableCell className="text-right tabular-nums">{hours(row.break_time)}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.late_logins}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.early_logouts}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            Page {page} of {pageCount}
          </p>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || isFetching}
            >
              <ChevronLeft className="h-4 w-4 mr-1" /> Previous
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              disabled={page >= pageCount || isFetching}
            >
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
