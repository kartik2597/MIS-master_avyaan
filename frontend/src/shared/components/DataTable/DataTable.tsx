import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState/EmptyState";
import { cn } from "@/lib/utils";
import type { ComponentType, ReactNode } from "react";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  empty?: string;
  emptyDescription?: string;
  emptyIcon?: ComponentType<{ className?: string }>;
  loading?: boolean;
  rowKey?: (row: T, i: number) => string | number;
}

const alignClass = { left: "", right: "text-right", center: "text-center" } as const;

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  empty = "No records found",
  emptyDescription,
  emptyIcon,
  loading = false,
  rowKey,
}: DataTableProps<T>) {
  return (
    <div className="rounded-xl border bg-card shadow-card overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              {columns.map((c) => (
                <TableHead
                  key={String(c.key)}
                  className={cn(
                    "h-11 px-4 text-xs font-semibold uppercase tracking-wide whitespace-nowrap",
                    alignClass[c.align ?? "left"],
                    c.className,
                  )}
                >
                  {c.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={`skeleton-${i}`} className="hover:bg-transparent">
                  {columns.map((c) => (
                    <TableCell key={String(c.key)} className="px-4 py-3.5">
                      <Skeleton className="h-4 w-full max-w-[140px]" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={columns.length} className="p-0">
                  <EmptyState title={empty} description={emptyDescription} icon={emptyIcon} />
                </TableCell>
              </TableRow>
            ) : (
              data.map((row, i) => (
                <TableRow key={rowKey ? rowKey(row, i) : i}>
                  {columns.map((c) => (
                    <TableCell
                      key={String(c.key)}
                      className={cn(
                        "px-4 py-3",
                        alignClass[c.align ?? "left"],
                        c.align === "right" && "tabular-nums",
                        c.className,
                      )}
                    >
                      {c.render ? c.render(row) : (row as any)[c.key]}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
