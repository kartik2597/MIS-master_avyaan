import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/shared/components/StatusBadge/StatusBadge";
import { Pager } from "@/shared/components/Pager/Pager";
import { EMPTY_TEAM, type TeamFilters } from "@/shared/components/Filters/DashboardFilters";
import { getErrorMessage } from "@/lib/api-client";
import { getHiringEvents } from "@/services/api/hiring";
import type { ExitReasonCount, HiringEventType, HiringTeamRow } from "@/services/api/types";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";

const PAGE_SIZE = 10;
const SEARCH_DELAY_MS = 300;

type EventFilter = "ALL" | HiringEventType;

const EVENT_FILTERS: { value: EventFilter; label: string }[] = [
  { value: "ALL", label: "All" },
  { value: "JOINED", label: "Joiners" },
  { value: "LEFT", label: "Leavers" },
];

interface TeamsProps {
  items: HiringTeamRow[];
  loading?: boolean;
  error?: string;
}

/** Joiners and leavers per team, the team with the most leavers first. */
export function TeamsTable({ items, loading, error }: TeamsProps) {
  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="space-y-0.5">
        <h3 className="text-sm font-semibold text-foreground">By team</h3>
        <p className="text-xs text-muted-foreground">Team with the most leavers first.</p>
      </div>
      {loading ? (
        <div className="space-y-2" role="status" aria-label="Loading teams">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No hiring or exit data for this period.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Team</TableHead>
              <TableHead className="text-right">Joiners</TableHead>
              <TableHead className="text-right">Leavers</TableHead>
              <TableHead className="text-right">Net</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((row) => (
              <TableRow key={row.team}>
                <TableCell className="font-medium text-foreground">{row.team}</TableCell>
                <TableCell className="text-right tabular-nums">{row.joiners}</TableCell>
                <TableCell className="text-right tabular-nums">{row.leavers}</TableCell>
                <TableCell
                  className={cn(
                    "text-right tabular-nums",
                    row.net_change < 0 && "text-destructive",
                    row.net_change > 0 && "text-success",
                  )}
                >
                  {row.net_change > 0 ? `+${row.net_change}` : row.net_change}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Card>
  );
}

/** The most common reasons people gave for leaving. */
export function ExitReasons({ reasons }: { reasons: ExitReasonCount[] }) {
  const most = Math.max(1, ...reasons.map((item) => item.count));

  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="space-y-0.5">
        <h3 className="text-sm font-semibold text-foreground">Top exit reasons</h3>
        <p className="text-xs text-muted-foreground">As written in the uploaded report.</p>
      </div>
      {reasons.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No exit reasons in this period. Add an Exit Reason column to the report to see them here.
        </p>
      ) : (
        <ul className="space-y-3">
          {reasons.map((item) => (
            <li key={item.reason} className="space-y-1">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate text-foreground">{item.reason}</span>
                <span className="tabular-nums text-muted-foreground">{item.count}</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted">
                <div
                  className="h-1.5 rounded-full bg-destructive/70"
                  style={{ width: `${(item.count / most) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

interface EventsProps {
  from: string;
  to: string;
  /** Process / manager / TL / employee filters from the dashboard. */
  team?: TeamFilters;
  disabled?: boolean;
}

/** Individual joiners and leavers, newest first, with a type filter and search. */
export function EventsTable({ from, to, team = EMPTY_TEAM, disabled }: EventsProps) {
  const [eventFilter, setEventFilter] = useState<EventFilter>("ALL");
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
  }, [from, to, eventFilter, team.process, team.manager, team.tl, team.emp_id]);

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ["dashboard", "hiring", "events", from, to, team, eventFilter, search, page],
    queryFn: () =>
      getHiringEvents({
        date_from: from || undefined,
        date_to: to || undefined,
        process: team.process || undefined,
        manager: team.manager || undefined,
        tl: team.tl || undefined,
        emp_id: team.emp_id.trim() || undefined,
        event_type: eventFilter === "ALL" ? undefined : eventFilter,
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
          <h3 className="text-sm font-semibold text-foreground">Joiners and leavers</h3>
          <p className="text-xs text-muted-foreground">
            {total.toLocaleString()} {total === 1 ? "record" : "records"}
            {search ? ` matching "${search}"` : ""}. Newest first.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {EVENT_FILTERS.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={eventFilter === option.value ? "default" : "outline"}
              onClick={() => setEventFilter(option.value)}
            >
              {option.label}
            </Button>
          ))}
          <div className="relative w-full sm:w-64">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search by name or employee ID"
              aria-label="Search joiners and leavers"
              className="pl-8"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2" role="status" aria-label="Loading joiners and leavers">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-destructive">{getErrorMessage(error, "Unable to load joiners and leavers.")}</p>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          {search ? "No records match your search." : "No hiring or exit records for this period."}
        </p>
      ) : (
        <div className={cn("transition-opacity", isFetching && "opacity-60")} aria-busy={isFetching}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>Designation</TableHead>
                <TableHead>Manager</TableHead>
                <TableHead>Reason / source</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((row) => (
                <TableRow key={`${row.emp_id}-${row.event_type}-${row.event_date}`}>
                  <TableCell>
                    <p className="font-medium text-foreground">{row.employee_name}</p>
                    <p className="text-xs text-muted-foreground">{row.emp_id}</p>
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      label={row.event_type === "JOINED" ? "Joined" : "Left"}
                      tone={row.event_type === "JOINED" ? "success" : "destructive"}
                    />
                  </TableCell>
                  <TableCell className="tabular-nums">{row.event_date}</TableCell>
                  <TableCell className="text-muted-foreground">{row.team}</TableCell>
                  <TableCell className="text-muted-foreground">{row.designation}</TableCell>
                  <TableCell className="text-muted-foreground">{row.manager_name}</TableCell>
                  <TableCell className="text-muted-foreground">{row.detail || "—"}</TableCell>
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
