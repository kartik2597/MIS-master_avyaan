import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DataTable } from "@/shared/components/DataTable/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuth } from "@/app/store/authStore";
import {
  createEmployee,
  deleteEmployee,
  listEmployees,
  updateEmployee,
} from "@/services/api/employees";
import type { Employee, EmployeePayload } from "@/services/api/types";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";

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

export function EmployeeMasterPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canWrite = user?.role === "ADMIN" || user?.role === "MIS";
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [form, setForm] = useState<EmployeePayload>(EMPTY_FORM);

  const employeesQuery = useQuery({
    queryKey: ["employees", page, search],
    queryFn: () => listEmployees({ page, page_size: 20, search }),
  });

  const saveMutation = useMutation({
    mutationFn: () => editing ? updateEmployee(editing.id, form) : createEmployee(form),
    onSuccess: () => {
      setDialogOpen(false);
      setEditing(null);
      setForm(EMPTY_FORM);
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteEmployee,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees"] }),
  });

  const rows = employeesQuery.data?.items ?? [];
  const total = employeesQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  const columns = useMemo(() => {
    const base = [
      { key: "emp_id", header: "Emp ID" },
      { key: "employee_name", header: "Name" },
      { key: "email", header: "Email" },
      { key: "mobile", header: "Mobile" },
      { key: "department", header: "Department" },
      { key: "process", header: "Process" },
      { key: "designation", header: "Designation" },
      { key: "manager_name", header: "Manager" },
      { key: "tl_name", header: "TL" },
      { key: "location", header: "Location" },
      {
        key: "employment_status",
        header: "Status",
        render: (row: Employee) => (
          <Badge variant="secondary" className={row.employment_status.toLowerCase() === "active" ? "bg-success/15 text-success" : ""}>
            {row.employment_status}
          </Badge>
        ),
      },
    ];

    if (!canWrite) return base;

    return [
      ...base,
      {
        key: "actions",
        header: "",
        align: "right" as const,
        render: (row: Employee) => (
          <div className="flex gap-1 justify-end">
            <Button
              size="icon"
              variant="ghost"
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
            <Button
              size="icon"
              variant="ghost"
              className="text-destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(row.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ),
      },
    ];
  }, [canWrite, deleteMutation]);

  function updateField(field: keyof EmployeePayload, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-semibold">Employee Master</h2>
          <p className="text-sm text-muted-foreground">Centralised registry from the backend employee APIs.</p>
        </div>
        {canWrite && (
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
            <DialogContent className="max-w-3xl">
              <DialogHeader>
                <DialogTitle>{editing ? "Edit Employee" : "Add Employee"}</DialogTitle>
              </DialogHeader>
              <form
                className="grid grid-cols-1 md:grid-cols-2 gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  saveMutation.mutate();
                }}
              >
                {(Object.keys(EMPTY_FORM) as Array<keyof EmployeePayload>).map((field) => (
                  <div className="space-y-1.5" key={field}>
                    <Label className="text-xs">{field.replaceAll("_", " ")}</Label>
                    <Input
                      type={field === "date_of_joining" ? "date" : field === "email" ? "email" : "text"}
                      value={form[field]}
                      onChange={(e) => updateField(field, e.target.value)}
                      required
                    />
                  </div>
                ))}
                <div className="md:col-span-2 flex justify-end gap-2 pt-2">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                  <Button type="submit" disabled={saveMutation.isPending}>
                    {saveMutation.isPending ? "Saving..." : "Save"}
                  </Button>
                </div>
                {saveMutation.error && (
                  <p className="md:col-span-2 text-sm text-destructive">Unable to save employee.</p>
                )}
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Card className="p-4">
        <div className="relative max-w-xl">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by Employee ID, name, email, department, process, manager or TL..."
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            className="pl-8"
          />
        </div>
      </Card>

      {employeesQuery.isLoading ? (
        <div className="text-sm text-muted-foreground">Loading employees...</div>
      ) : employeesQuery.error ? (
        <div className="text-sm text-destructive">Unable to load employees.</div>
      ) : (
        <>
          <DataTable columns={columns} data={rows} rowKey={(row) => row.id} />
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{total.toLocaleString()} employees</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
              <span>Page {page} of {totalPages}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
