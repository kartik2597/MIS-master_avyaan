import { useEffect, useMemo, useState, type ReactNode } from "react";
import { format, parseISO } from "date-fns";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getErrorMessage } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { DataTable, type Column } from "@/shared/components/DataTable/DataTable";
import { ConfirmDeleteButton } from "@/shared/components/ConfirmDelete/ConfirmDeleteButton";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { StatusBadge } from "@/shared/components/StatusBadge/StatusBadge";
import { useAuth } from "@/app/store/authStore";
import {
  createEmployee,
  deleteEmployee,
  listEmployees,
  updateEmployee,
} from "@/services/api/employees";
import type { Employee, EmployeePayload } from "@/services/api/types";
import { Info, Pencil, Plus, Search, Users } from "lucide-react";

const PAGE_SIZE = 20;

const EMPTY_FORM: EmployeePayload = {
  emp_id: "",
  employee_name: "",
  email: "",
  mobile: "",
  department: "",
  process: "",
  designation: "",
  manager_name: "",
  tl_name: "",
  date_of_joining: new Date().toISOString().slice(0, 10),
  employment_status: "Active",
  location: "",
};

/** Details that reports and roster uploads cannot supply. Only a master database upload or an edit fills them in. */
const CONTACT_FIELDS: { key: keyof Employee; label: string }[] = [
  { key: "email", label: "email" },
  { key: "mobile", label: "mobile" },
  { key: "manager_name", label: "manager" },
  { key: "tl_name", label: "TL" },
  { key: "location", label: "location" },
];

function isBlank(value: unknown) {
  return value === null || value === undefined || String(value).trim() === "";
}

function missingDetails(row: Employee) {
  return CONTACT_FIELDS.filter((field) => isBlank(row[field.key])).map((field) => field.label);
}

/** Shows a muted dash instead of an empty cell. */
function orDash(value: string | null | undefined): ReactNode {
  return isBlank(value) ? <span className="text-muted-foreground/60">—</span> : value;
}

function formatJoined(value: string) {
  try {
    return format(parseISO(value), "d MMM yyyy");
  } catch {
    return value;
  }
}

function initials(name: string) {
  return (
    name
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "?"
  );
}

export function EmployeeMasterPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canWrite = user?.role === "ADMIN" || user?.role === "MIS";
  // What is typed, and the value actually searched (after a short pause in typing).
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [form, setForm] = useState<EmployeePayload>(EMPTY_FORM);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const employeesQuery = useQuery({
    queryKey: ["employees", page, search],
    queryFn: () => listEmployees({ page, page_size: PAGE_SIZE, search }),
    placeholderData: keepPreviousData,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!editing) return createEmployee(form);
      // Send only what changed and is not blank, so an employee with missing
      // details can be corrected a field at a time.
      const changes: Partial<EmployeePayload> = {};
      (Object.keys(form) as Array<keyof EmployeePayload>).forEach((field) => {
        const value = form[field].trim();
        if (value !== "" && value !== (editing[field] ?? "")) changes[field] = value;
      });
      return updateEmployee(editing.id, changes);
    },
    onSuccess: () => {
      setDialogOpen(false);
      setEditing(null);
      setForm(EMPTY_FORM);
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteEmployee,
    onSuccess: () => {
      // Deleting the only row on the last page would leave an empty page.
      if (page > 1 && (employeesQuery.data?.items.length ?? 0) <= 1) {
        setPage((p) => p - 1);
      }
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  const rows = employeesQuery.data?.items ?? [];
  const total = employeesQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const deleting = deleteMutation.isPending;
  const deleteEmployeeById = deleteMutation.mutate;

  const columns = useMemo<Column<Employee>[]>(() => {
    const base: Column<Employee>[] = [
      {
        key: "emp_id",
        header: "Emp ID",
        render: (row) => <span className="font-mono text-xs text-muted-foreground">{row.emp_id}</span>,
      },
      {
        key: "employee_name",
        header: "Name",
        render: (row) => {
          const missing = missingDetails(row);
          return (
            <div className="flex items-center gap-2.5 whitespace-nowrap">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-semibold">
                  {initials(row.employee_name)}
                </AvatarFallback>
              </Avatar>
              <span className="font-medium text-foreground">{row.employee_name}</span>
              {missing.length > 0 && (
                <span title={`Missing: ${missing.join(", ")}`}>
                  <StatusBadge label="Incomplete" tone="warning" />
                </span>
              )}
            </div>
          );
        },
      },
      { key: "email", header: "Email", className: "text-muted-foreground", render: (row) => orDash(row.email) },
      { key: "mobile", header: "Mobile", className: "whitespace-nowrap", render: (row) => orDash(row.mobile) },
      { key: "department", header: "Department", className: "whitespace-nowrap", render: (row) => orDash(row.department) },
      { key: "process", header: "Process", className: "whitespace-nowrap", render: (row) => orDash(row.process) },
      { key: "designation", header: "Designation", className: "whitespace-nowrap", render: (row) => orDash(row.designation) },
      { key: "manager_name", header: "Manager", className: "whitespace-nowrap", render: (row) => orDash(row.manager_name) },
      { key: "tl_name", header: "TL", className: "whitespace-nowrap", render: (row) => orDash(row.tl_name) },
      { key: "location", header: "Location", className: "whitespace-nowrap", render: (row) => orDash(row.location) },
      {
        key: "date_of_joining",
        header: "Joined",
        className: "whitespace-nowrap tabular-nums text-muted-foreground",
        render: (row) => formatJoined(row.date_of_joining),
      },
      {
        key: "employment_status",
        header: "Status",
        render: (row) => (
          <StatusBadge
            label={row.employment_status}
            tone={row.employment_status.toLowerCase() === "active" ? "success" : "neutral"}
          />
        ),
      },
    ];

    if (!canWrite) return base;

    return [
      ...base,
      {
        key: "actions",
        header: "Actions",
        align: "right",
        // Pinned to the right so edit/delete stay visible on narrow screens.
        className: "sticky right-0 z-10 bg-card shadow-[-8px_0_8px_-8px_rgba(0,0,0,0.15)]",
        render: (row) => (
          <div className="flex gap-1 justify-end">
            <Button
              size="icon"
              variant="ghost"
              aria-label={`Edit ${row.employee_name}`}
              onClick={() => {
                setEditing(row);
                setForm({
                  emp_id: row.emp_id,
                  employee_name: row.employee_name,
                  email: row.email,
                  mobile: row.mobile,
                  department: row.department,
                  process: row.process,
                  designation: row.designation,
                  manager_name: row.manager_name,
                  tl_name: row.tl_name,
                  date_of_joining: row.date_of_joining,
                  employment_status: row.employment_status,
                  location: row.location,
                });
                setDialogOpen(true);
              }}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <ConfirmDeleteButton
              title="Delete employee?"
              description={`This will permanently delete ${row.employee_name} (${row.emp_id}). This cannot be undone.`}
              disabled={deleting}
              onConfirm={() => deleteEmployeeById(row.id)}
            />
          </div>
        ),
      },
    ];
  }, [canWrite, deleting, deleteEmployeeById]);

  function updateField(field: keyof EmployeePayload, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  const firstRow = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastRow = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Employee Master"
        description="Centralised registry of every employee, searchable by ID, name, team or process."
        actions={
          canWrite && (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  onClick={() => {
                    setEditing(null);
                    setForm(EMPTY_FORM);
                  }}
                >
                  <Plus className="h-4 w-4 mr-2" /> Add Employee
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>{editing ? "Edit Employee" : "Add Employee"}</DialogTitle>
                  <DialogDescription>
                    {editing
                      ? "Fill in any missing details. Fields you leave blank are not changed."
                      : "All fields are required."}
                  </DialogDescription>
                </DialogHeader>
                <form
                  className="grid grid-cols-1 md:grid-cols-2 gap-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    saveMutation.mutate();
                  }}
                >
                  {(Object.keys(EMPTY_FORM) as Array<keyof EmployeePayload>).map((field) => (
                    <div className="space-y-1.5" key={field}>
                      <Label htmlFor={`emp-${field}`} className="text-xs capitalize">
                        {field.replaceAll("_", " ")}
                      </Label>
                      <Input
                        id={`emp-${field}`}
                        type={field === "date_of_joining" ? "date" : field === "email" ? "email" : "text"}
                        value={form[field]}
                        onChange={(e) => updateField(field, e.target.value)}
                        // When editing, a detail that was never filled in can stay blank.
                        required={!editing || !isBlank(editing[field])}
                      />
                    </div>
                  ))}
                  {saveMutation.error && (
                    <div className="md:col-span-2">
                      <ErrorState
                        title="Couldn't save employee"
                        message={getErrorMessage(saveMutation.error, "Unable to save employee.")}
                      />
                    </div>
                  )}
                  <div className="md:col-span-2 flex justify-end gap-2 pt-2">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={saveMutation.isPending}>
                      {saveMutation.isPending ? "Saving..." : "Save"}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          )
        }
      />

      <Card className="p-4 shadow-card">
        <div className="relative max-w-xl">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            aria-label="Search employees"
            placeholder="Search by ID, name, email, department, process, manager or TL..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>
      </Card>

      {employeesQuery.error && !employeesQuery.data ? (
        <ErrorState
          title="Unable to load employees"
          message={getErrorMessage(employeesQuery.error, "Unable to load employees.")}
        />
      ) : (
        <div className="space-y-3">
          {rows.some((row) => missingDetails(row).length > 0) && (
            <div className="flex items-start gap-2 rounded-lg border border-info/30 bg-info/10 px-3 py-2.5 text-sm">
              <Info className="h-4 w-4 mt-0.5 shrink-0 text-info" />
              <p className="text-muted-foreground">
                Employees marked <span className="font-medium text-foreground">Incomplete</span> came from uploaded
                reports, which do not include email, mobile, manager, TL or location. Upload a Master Database file
                to fill them in, or edit an employee directly.
              </p>
            </div>
          )}
          <DataTable
            columns={columns}
            data={rows}
            loading={employeesQuery.isLoading}
            rowKey={(row) => row.id}
            empty={search ? "No employees match your search" : "No employees yet"}
            emptyDescription={
              search ? "Try a different name, ID or department." : canWrite ? "Use “Add Employee” to create the first record." : undefined
            }
            emptyIcon={Users}
          />
          {total > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
              <span>
                Showing {firstRow.toLocaleString()}–{lastRow.toLocaleString()} of {total.toLocaleString()} employees
              </span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <span className="tabular-nums">
                  Page {page} of {totalPages}
                </span>
                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {deleteMutation.error && (
        <ErrorState
          title="Couldn't delete employee"
          message={getErrorMessage(deleteMutation.error, "Unable to delete employee.")}
        />
      )}
    </div>
  );
}
