import { useMemo } from "react";
import { format, parseISO } from "date-fns";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ProjectHoursRow, ProjectTrendPoint } from "@/services/api/types";
import { ChartCard } from "../../agent/components/ChartCard";

// These read the theme variables in styles.css, so the charts follow light and dark mode.
const GRID_STROKE = "var(--border)";
const AXIS_STYLE = { fontSize: 12, fill: "var(--muted-foreground)" };
const TOOLTIP_STYLE = {
  borderRadius: 8,
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  border: "1px solid var(--border)",
};
const TOP_PROJECTS = 8;

function dayLabel(value: unknown) {
  try {
    return format(parseISO(String(value)), "d MMM");
  } catch {
    return String(value);
  }
}

function hoursLabel(value: unknown) {
  return typeof value === "number"
    ? `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} hrs`
    : String(value);
}

interface TrendProps {
  points: ProjectTrendPoint[];
  loading?: boolean;
  error?: string;
}

/** Billable and non-billable hours, day by day. */
export function HoursTrendChart({ points, loading, error }: TrendProps) {
  const data = useMemo(
    () =>
      points.map((point) => ({
        report_date: point.report_date,
        billable: point.billable_hours,
        non_billable: Math.max(point.total_hours - point.billable_hours, 0),
      })),
    [points],
  );

  return (
    <ChartCard
      title="Hours per day"
      description="Total hours logged across all projects, split into billable and non-billable."
      loading={loading}
      error={error}
      empty={data.length === 0}
      emptyText="No timesheet data for this period."
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="report_date" tickFormatter={dayLabel} tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <Tooltip
            labelFormatter={dayLabel}
            formatter={(value) => hoursLabel(value)}
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: "rgba(148, 163, 184, 0.15)" }}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="billable" name="Billable" stackId="hours" fill="var(--chart-2)" />
          <Bar
            dataKey="non_billable"
            name="Non-billable"
            stackId="hours"
            fill="var(--chart-3)"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

interface ProjectsProps {
  items: ProjectHoursRow[];
  loading?: boolean;
  error?: string;
}

/** The projects that took the most hours in the period. */
export function HoursByProjectChart({ items, loading, error }: ProjectsProps) {
  const top = items.slice(0, TOP_PROJECTS);

  return (
    <ChartCard
      title="Hours by project"
      description={
        items.length > TOP_PROJECTS
          ? `The ${TOP_PROJECTS} busiest of ${items.length} projects.`
          : "Total hours logged on each project."
      }
      loading={loading}
      error={error}
      empty={top.length === 0}
      emptyText="No timesheet data for this period."
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={top} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
          <XAxis type="number" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <YAxis
            type="category"
            dataKey="project_name"
            width={120}
            tick={AXIS_STYLE}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            formatter={(value) => hoursLabel(value)}
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: "rgba(148, 163, 184, 0.15)" }}
          />
          <Bar dataKey="total_hours" name="Hours" fill="var(--chart-1)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
