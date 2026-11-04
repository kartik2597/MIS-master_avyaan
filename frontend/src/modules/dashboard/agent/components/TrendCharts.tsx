import { format, parseISO } from "date-fns";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTrendPoint } from "@/services/api/types";
import { ChartCard } from "./ChartCard";

// These read the theme variables in styles.css, so the charts follow light and dark mode.
const COLORS = {
  blue: "var(--chart-1)",
  green: "var(--chart-2)",
  amber: "var(--chart-3)",
  red: "var(--destructive)",
  slate: "var(--muted-foreground)",
};

const GRID_STROKE = "var(--border)";
const AXIS_STYLE = { fontSize: 12, fill: "var(--muted-foreground)" };

interface TrendChartProps {
  points: DashboardTrendPoint[];
  loading?: boolean;
  error?: string;
}

function dayLabel(value: unknown) {
  try {
    return format(parseISO(String(value)), "d MMM");
  } catch {
    return String(value);
  }
}

function numberLabel(value: unknown) {
  return typeof value === "number"
    ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : String(value);
}

const TOOLTIP_STYLE = {
  borderRadius: 8,
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  border: "1px solid var(--border)",
};

/** Head count and present agents, day by day. */
export function PeopleTrendChart({ points, loading, error }: TrendChartProps) {
  return (
    <ChartCard
      title="Head count vs present"
      description="Agents on the roster and agents who were present, per day."
      loading={loading}
      error={error}
      empty={points.length === 0}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="report_date" tickFormatter={dayLabel} tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip labelFormatter={dayLabel} formatter={(value) => numberLabel(value)} contentStyle={TOOLTIP_STYLE} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="head_count"
            name="Head count"
            stroke={COLORS.slate}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="present_count"
            name="Present"
            stroke={COLORS.green}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

/** Shift adherence % and overall shrinkage %, day by day. Days without data are gaps. */
export function RateTrendChart({ points, loading, error }: TrendChartProps) {
  return (
    <ChartCard
      title="Adherence and shrinkage"
      description="Both are percentages. A gap means that report has no data for the day."
      loading={loading}
      error={error}
      empty={points.length === 0}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="report_date" tickFormatter={dayLabel} tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <YAxis
            tick={AXIS_STYLE}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip
            labelFormatter={dayLabel}
            formatter={(value) => `${numberLabel(value)}%`}
            contentStyle={TOOLTIP_STYLE}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="adherence_percent"
            name="Shift adherence"
            stroke={COLORS.blue}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="overall_shrinkage"
            name="Overall shrinkage"
            stroke={COLORS.amber}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

/** Talk time next to staff time, in hours, day by day. */
export function TimeTrendChart({ points, loading, error }: TrendChartProps) {
  return (
    <ChartCard
      title="Talk time vs staff time"
      description="Total hours across all agents, per day."
      loading={loading}
      error={error}
      empty={points.length === 0}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="report_date" tickFormatter={dayLabel} tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <Tooltip
            labelFormatter={dayLabel}
            formatter={(value) => `${numberLabel(value)} hrs`}
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: "rgba(148, 163, 184, 0.15)" }}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="staff_time" name="Staff time" fill={COLORS.slate} radius={[4, 4, 0, 0]} />
          <Bar dataKey="talk_time" name="Talk time" fill={COLORS.blue} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
