import { Card } from "@/components/ui/card";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  AreaChart,
  Area,
} from "recharts";

interface Series {
  key: string;
  name: string;
  color?: string;
}

interface TrendChartProps {
  title: string;
  subtitle?: string;
  data: Array<Record<string, any>>;
  xKey: string;
  series: Series[];
  type?: "line" | "bar" | "area";
  height?: number;
}

const palette = ["var(--color-chart-1)", "var(--color-chart-2)", "var(--color-chart-3)", "var(--color-chart-4)", "var(--color-chart-5)"];

export function TrendChart({ title, subtitle, data, xKey, series, type = "line", height = 260 }: TrendChartProps) {
  const Chart = type === "bar" ? BarChart : type === "area" ? AreaChart : LineChart;

  return (
    <Card className="p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <div style={{ width: "100%", height }}>
        <ResponsiveContainer>
          <Chart data={data} margin={{ top: 5, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis dataKey={xKey} stroke="var(--color-muted-foreground)" fontSize={11} />
            <YAxis stroke="var(--color-muted-foreground)" fontSize={11} />
            <Tooltip
              contentStyle={{
                background: "var(--color-popover)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {series.map((s, i) => {
              const color = s.color ?? palette[i % palette.length];
              if (type === "bar") return <Bar key={s.key} dataKey={s.key} name={s.name} fill={color} radius={[4, 4, 0, 0]} />;
              if (type === "area")
                return (
                  <Area key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={color} fill={color} fillOpacity={0.2} />
                );
              return <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={color} strokeWidth={2} dot={false} />;
            })}
          </Chart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
