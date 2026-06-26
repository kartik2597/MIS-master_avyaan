import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ReactNode } from "react";

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
  rowKey?: (row: T, i: number) => string | number;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  empty = "No records found",
  rowKey,
}: DataTableProps<T>) {
  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/40 hover:bg-muted/40">
            {columns.map((c) => (
              <TableHead
                key={String(c.key)}
                className={`${c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : ""} ${c.className ?? ""}`}
              >
                {c.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-center py-10 text-muted-foreground">
                {empty}
              </TableCell>
            </TableRow>
          ) : (
            data.map((row, i) => (
              <TableRow key={rowKey ? rowKey(row, i) : i}>
                {columns.map((c) => (
                  <TableCell
                    key={String(c.key)}
                    className={`${c.align === "right" ? "text-right tabular-nums" : c.align === "center" ? "text-center" : ""} ${c.className ?? ""}`}
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
  );
}
