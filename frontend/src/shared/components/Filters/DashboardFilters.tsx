import { useQuery } from "@tanstack/react-query";
import { endOfMonth, format, startOfMonth, subDays } from "date-fns";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { getDashboardFilterOptions } from "@/services/api/dashboard";
import { CalendarRange, RotateCcw, Users } from "lucide-react";

export interface DateRange {
  from: string; // YYYY-MM-DD or ""
  to: string; // YYYY-MM-DD or ""
}

/** Who to look at. An empty string means "everyone". */
export interface TeamFilters {
  process: string;
  manager: string;
  tl: string;
  emp_id: string;
}

export const EMPTY_TEAM: TeamFilters = { process: "", manager: "", tl: "", emp_id: "" };

interface FiltersProps {
  value: DateRange;
  onChange: (value: DateRange) => void;
  /** Pass both to show the process / manager / TL / employee filters. */
  team?: TeamFilters;
  onTeamChange?: (value: TeamFilters) => void;
}

const iso = (d: Date) => format(d, "yyyy-MM-dd");

function presets(): { label: string; range: DateRange }[] {
  const today = new Date();
  return [
    { label: "Last 7 days", range: { from: iso(subDays(today, 6)), to: iso(today) } },
    { label: "Last 30 days", range: { from: iso(subDays(today, 29)), to: iso(today) } },
    { label: "This month", range: { from: iso(startOfMonth(today)), to: iso(endOfMonth(today)) } },
  ];
}

const SELECT_CLASS =
  "h-9 w-44 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

interface TeamSelectProps {
  id: string;
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}

function TeamSelect({ id, label, value, options, onChange }: TeamSelectProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">{label}</Label>
      <select id={id} className={SELECT_CLASS} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}

export function DashboardFilters({ value, onChange, team, onTeamChange }: FiltersProps) {
  const invalid = Boolean(value.from && value.to && value.from > value.to);
  const hasRange = Boolean(value.from || value.to);
  const showTeam = Boolean(team && onTeamChange);
  const hasTeam = Boolean(team && (team.process || team.manager || team.tl || team.emp_id));

  // The drop-downs only list names this user is allowed to see.
  const { data: options } = useQuery({
    queryKey: ["dashboard", "filters"],
    queryFn: getDashboardFilterOptions,
    enabled: showTeam,
    staleTime: 5 * 60 * 1000,
  });

  const setTeam = (patch: Partial<TeamFilters>) => {
    if (team && onTeamChange) onTeamChange({ ...team, ...patch });
  };

  return (
    <Card className="p-4 shadow-card space-y-4">
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground self-center">
          <CalendarRange className="h-4 w-4" />
          Period
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="date-from" className="text-xs text-muted-foreground">From</Label>
          <Input
            id="date-from"
            type="date"
            className="w-40"
            value={value.from}
            max={value.to || undefined}
            onChange={(e) => onChange({ ...value, from: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="date-to" className="text-xs text-muted-foreground">To</Label>
          <Input
            id="date-to"
            type="date"
            className="w-40"
            value={value.to}
            min={value.from || undefined}
            onChange={(e) => onChange({ ...value, to: e.target.value })}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {presets().map((p) => {
            const active = value.from === p.range.from && value.to === p.range.to;
            return (
              <Button
                key={p.label}
                type="button"
                size="sm"
                variant={active ? "default" : "outline"}
                onClick={() => onChange(p.range)}
              >
                {p.label}
              </Button>
            );
          })}
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onChange({ from: "", to: "" })}
            disabled={!hasRange}
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Latest day
          </Button>
        </div>
      </div>

      {showTeam && team && (
        <div className="flex flex-wrap items-end gap-x-4 gap-y-3 border-t pt-4">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground self-center">
            <Users className="h-4 w-4" />
            Team
          </div>
          <TeamSelect
            id="filter-process"
            label="Process"
            value={team.process}
            options={options?.processes ?? []}
            onChange={(process) => setTeam({ process })}
          />
          <TeamSelect
            id="filter-manager"
            label="Manager"
            value={team.manager}
            options={options?.managers ?? []}
            onChange={(manager) => setTeam({ manager })}
          />
          <TeamSelect
            id="filter-tl"
            label="Team Lead"
            value={team.tl}
            options={options?.tls ?? []}
            onChange={(tl) => setTeam({ tl })}
          />
          <div className="space-y-1.5">
            <Label htmlFor="filter-emp" className="text-xs text-muted-foreground">Employee ID</Label>
            <Input
              id="filter-emp"
              className="w-40"
              placeholder="e.g. 10234"
              value={team.emp_id}
              onChange={(e) => setTeam({ emp_id: e.target.value })}
            />
          </div>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onTeamChange?.(EMPTY_TEAM)}
            disabled={!hasTeam}
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Clear team
          </Button>
        </div>
      )}
      {invalid && <p className="text-xs text-destructive">"From" must be on or before "To".</p>}
    </Card>
  );
}
