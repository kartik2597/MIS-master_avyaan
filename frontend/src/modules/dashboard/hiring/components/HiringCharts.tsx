import { format, parseISO } from "date-fns";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HiringTrendPoint } from "@/services/api/types";
import { ChartCard } from "../../agent/components/ChartCard";

// These read the theme variables in styles.css, so the chart follows light and dark mode.
const GRID_STROKE = "var(--border)";
const AXIS_STYLE = { fontSize: 12, fill: "var(--muted-foreground)" };
const TOOLTIP_STYLE = {
  borderRadius: 8,
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  border: "1px solid var(--border)",
};

function monthLabel(value: unknown) {
  try {
    return format(parseISO(`${String(value)}-01`), "MMM yy");
  } catch {
    return String(value);
  }
}

interface Props {
  points: HiringTrendPoint[];
  loading?: boolean;
  error?: string;
}

/** Joiners next to leavers, month by month. */
export function HiringTrendChart({ points, loading, error }: Props) {
  return (
    <ChartCard
      title="Joiners and leavers"
      description="People who joined and people who left, per calendar month."
      loading={loading}
      error={error}
      empty={points.length === 0}
      emptyText="No hiring or exit data for this period."
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
          <XAxis dataKey="month" tickFormatter={monthLabel} tick={AXIS_STYLE} tickLine={false} axisLine={false} />
          <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip
            labelFormatter={monthLabel}
            contentStyle={TOOLTIP_STYLE}
            cursor={{ fill: "rgba(148, 163, 184, 0.15)" }}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="joiners" name="Joiners" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="leavers" name="Leavers" fill="var(--destructive)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
