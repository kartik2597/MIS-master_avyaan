import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { AttendanceBreakdown as AttendanceData } from "@/services/api/types";
import { ChartCard } from "./ChartCard";

const STATUS_COLORS: Record<string, string> = {
  Present: "#16a34a",
  Absent: "#dc2626",
  Leave: "#d97706",
  LWP: "#ea580c",
  "Half Day": "#2563eb",
  Training: "#0891b2",
  Other: "#94a3b8",
};

interface AttendanceBreakdownProps {
  data?: AttendanceData;
  loading?: boolean;
  error?: string;
}

/** Present / absent / leave split for the period, as a donut with a plain legend. */
export function AttendanceBreakdown({ data, loading, error }: AttendanceBreakdownProps) {
  const slices = data?.slices ?? [];
  const total = data?.total ?? 0;

  return (
    <ChartCard
      title="Attendance"
      description="Agent-days by status for the selected period."
      loading={loading}
      error={error}
      empty={slices.length === 0}
      emptyText="No attendance data for this period."
    >
      <div className="flex h-full flex-col gap-3">
        <div className="relative h-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={slices}
                dataKey="count"
                nameKey="status"
                innerRadius={44}
                outerRadius={64}
                paddingAngle={2}
                stroke="none"
              >
                {slices.map((slice) => (
                  <Cell key={slice.status} fill={STATUS_COLORS[slice.status] ?? STATUS_COLORS.Other} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  fontSize: 12,
                  backgroundColor: "var(--popover)",
                  color: "var(--popover-foreground)",
                  border: "1px solid var(--border)",
                }}
                itemStyle={{ color: "var(--popover-foreground)" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-semibold tabular-nums">{total.toLocaleString()}</span>
            <span className="text-[11px] text-muted-foreground">total</span>
          </div>
        </div>

        <ul className="space-y-1.5 overflow-auto text-sm">
          {slices.map((slice) => {
            const percent = total > 0 ? (slice.count / total) * 100 : 0;
            return (
              <li key={slice.status} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: STATUS_COLORS[slice.status] ?? STATUS_COLORS.Other }}
                />
                <span className="flex-1 text-muted-foreground">{slice.status}</span>
                <span className="font-medium tabular-nums">{slice.count.toLocaleString()}</span>
                <span className="w-12 text-right text-xs text-muted-foreground tabular-nums">
                  {percent.toFixed(1)}%
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </ChartCard>
  );
}
