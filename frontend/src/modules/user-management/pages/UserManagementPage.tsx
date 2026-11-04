import { useState } from "react";
import { format, parseISO } from "date-fns";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { DataTable, type Column } from "@/shared/components/DataTable/DataTable";
import { StatusBadge } from "@/shared/components/StatusBadge/StatusBadge";
import { useAuth } from "@/app/store/authStore";
import { createUser, listUsers, setUserEmployee } from "@/services/api/auth";
import { getErrorMessage } from "@/lib/api-client";
import type { Role, User, UserCreatePayload } from "@/services/api/types";
import { cn } from "@/lib/utils";
import { CheckCircle2, Eye, EyeOff, Loader2, Search, UserPlus, Users, Wand2 } from "lucide-react";

const EMPTY_FORM: UserCreatePayload = {
  full_name: "",
  email: "",
  password: "",
  role: "MIS",
  is_active: true,
  emp_id: "",
};

const ROLES: Role[] = ["ADMIN", "MIS", "MANAGER", "TL"];

const ROLE_HELP: Record<Role, string> = {
  ADMIN: "Full access, including creating users.",
  MIS: "Uploads reports and manages employees and uploads.",
  MANAGER: "Views the dashboards for their own team. Needs an Employee ID.",
  TL: "Views the dashboards for their own team. Needs an Employee ID.",
};

const needsEmployeeId = (role: Role) => role === "MANAGER" || role === "TL";

const ROLE_TONE: Record<Role, "info" | "success" | "warning" | "neutral"> = {
  ADMIN: "info",
  MIS: "success",
  MANAGER: "warning",
  TL: "neutral",
};

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

function formatCreated(value: string) {
  try {
    return format(parseISO(value), "d MMM yyyy");
  } catch {
    return value;
  }
}

const STRENGTH_LEVELS = [
  { label: "Too short", bar: "bg-destructive" },
  { label: "Weak", bar: "bg-destructive" },
  { label: "Fair", bar: "bg-warning" },
  { label: "Good", bar: "bg-info" },
  { label: "Strong", bar: "bg-success" },
];

/** 0 (under 8 characters) to 4. One point each for length 12+, mixed case, a digit and a symbol. */
function passwordStrength(password: string) {
  if (password.length < 8) return 0;
  const points = [
    password.length >= 12,
    /[a-z]/.test(password) && /[A-Z]/.test(password),
    /\d/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ].filter(Boolean).length;
  return Math.max(1, points);
}

/** A random 14-character password from the browser's secure random source. */
function generatePassword() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
  const values = new Uint32Array(14);
  crypto.getRandomValues(values);
  return Array.from(values, (value) => chars[value % chars.length]).join("");
}

/**
 * Shows and edits the Employee ID a login is linked to. MANAGER and TL users are
 * limited to the team under that employee, so without an ID they see no data.
 */
function EmployeeIdCell({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [value, setValue] = useState(user.emp_id ?? "");
  const mutation = useMutation({
    mutationFn: (empId: string | null) => setUserEmployee(user.id, empId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
  const changed = value.trim() !== (user.emp_id ?? "");
  const required = needsEmployeeId(user.role);

  return (
    <form
      className="flex items-center gap-1.5"
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate(value.trim() || null);
      }}
    >
      <Input
        aria-label={`Employee ID for ${user.full_name}`}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={required ? "Required" : "Optional"}
        maxLength={50}
        className={cn("h-8 w-28 text-xs", required && !user.emp_id && "border-warning")}
      />
      {changed && (
        <Button type="submit" size="sm" className="h-8 px-2 text-xs" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Save"}
        </Button>
      )}
      {mutation.error && (
        <span className="text-xs text-destructive" role="alert">
          {getErrorMessage(mutation.error, "Couldn't save.")}
        </span>
      )}
    </form>
  );
}

export function UserManagementPage() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [userSearch, setUserSearch] = useState("");
  const [form, setForm] = useState<UserCreatePayload>(EMPTY_FORM);
  const [createdUser, setCreatedUser] = useState<{ name: string; role: Role } | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: (user) => {
      setCreatedUser({ name: user.full_name, role: user.role });
      setForm(EMPTY_FORM);
      setShowPassword(false);
      // The new user should show up in the list straight away.
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const usersQuery = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const allUsers = usersQuery.data ?? [];
  const needle = userSearch.trim().toLowerCase();
  const users = needle
    ? allUsers.filter((u) =>
        [u.full_name, u.email, u.role].some((value) => value.toLowerCase().includes(needle)),
      )
    : allUsers;

  const userColumns: Column<User>[] = [
    {
      key: "full_name",
      header: "Name",
      render: (row) => (
        <div className="flex items-center gap-2.5 whitespace-nowrap">
          <Avatar className="h-7 w-7">
            <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-semibold">
              {initials(row.full_name)}
            </AvatarFallback>
          </Avatar>
          <span className="font-medium text-foreground">{row.full_name}</span>
          {row.id === currentUser?.id && <StatusBadge label="You" tone="info" />}
        </div>
      ),
    },
    { key: "email", header: "Email", className: "text-muted-foreground" },
    { key: "role", header: "Role", render: (row) => <StatusBadge label={row.role} tone={ROLE_TONE[row.role]} /> },
    { key: "emp_id", header: "Employee ID", render: (row) => <EmployeeIdCell user={row} /> },
    {
      key: "is_active",
      header: "Status",
      render: (row) => (
        <StatusBadge label={row.is_active ? "Active" : "Inactive"} tone={row.is_active ? "success" : "neutral"} />
      ),
    },
    {
      key: "created_at",
      header: "Created",
      className: "whitespace-nowrap tabular-nums text-muted-foreground",
      render: (row) => formatCreated(row.created_at),
    },
  ];

  const strength = passwordStrength(form.password);

  return (
    <div className="space-y-6">
      <PageHeader title="User Management" description="Create new users, choose their access level and see everyone who has an account." />

      {createMutation.isSuccess && createdUser && (
        <div
          role="status"
          className="flex gap-2 rounded-lg bg-success/10 border border-success/20 p-3 text-sm text-success max-w-2xl"
        >
          <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
          <p>
            {createdUser.name ? <span className="font-medium">{createdUser.name}</span> : "User"} was created with{" "}
            {createdUser.role} access.
          </p>
        </div>
      )}

      <Card className="p-6 shadow-card max-w-2xl">
        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            setCreatedUser(null);
            createMutation.mutate(form);
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="new-name">Full Name</Label>
              <Input
                id="new-name"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-email">Email</Label>
              <Input
                id="new-email"
                type="email"
                autoComplete="off"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="new-password">Password</Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  minLength={8}
                  className="pr-10"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1.5 rounded-md"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {form.password ? (
                <div className="space-y-1" aria-live="polite">
                  <div className="flex gap-1" aria-hidden="true">
                    {[1, 2, 3, 4].map((step) => (
                      <span
                        key={step}
                        className={cn(
                          "h-1 flex-1 rounded-full transition-colors",
                          strength >= step ? STRENGTH_LEVELS[strength].bar : "bg-muted",
                        )}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">Password strength: {STRENGTH_LEVELS[strength].label}</p>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">At least 8 characters.</p>
              )}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="-ml-2 h-7 text-xs text-muted-foreground"
                onClick={() => {
                  setForm({ ...form, password: generatePassword() });
                  setShowPassword(true); // so the admin can read it and pass it on
                }}
              >
                <Wand2 className="h-3.5 w-3.5 mr-1.5" /> Generate a password
              </Button>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-role">Role</Label>
              <Select value={form.role} onValueChange={(value) => setForm({ ...form, role: value as Role })}>
                <SelectTrigger id="new-role"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>{role}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">{ROLE_HELP[form.role]}</p>
            </div>
          </div>

          <div className="space-y-1.5 md:max-w-[calc(50%-0.5rem)]">
            <Label htmlFor="new-emp-id">
              Employee ID{needsEmployeeId(form.role) ? "" : " (optional)"}
            </Label>
            <Input
              id="new-emp-id"
              value={form.emp_id ?? ""}
              maxLength={50}
              onChange={(e) => setForm({ ...form, emp_id: e.target.value })}
              required={needsEmployeeId(form.role)}
            />
            <p className="text-xs text-muted-foreground">
              Must match an ID in the employee master. Managers and TLs only see the team under this employee.
            </p>
          </div>

          {createMutation.error && (
            <ErrorState
              title="Couldn't create user"
              message={getErrorMessage(createMutation.error, "Unable to create user.")}
            />
          )}

          <div className="flex justify-end pt-1">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4 mr-2" /> Create User
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="space-y-0.5">
            <h3 className="text-sm font-semibold text-foreground">All users</h3>
            <p className="text-xs text-muted-foreground">
              {allUsers.length.toLocaleString()} {allUsers.length === 1 ? "user" : "users"}
              {needle ? `, ${users.length.toLocaleString()} matching "${userSearch.trim()}"` : ""}
            </p>
          </div>
          <div className="relative w-full sm:w-72">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              aria-label="Search users"
              placeholder="Search by name, email or role"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>

        {usersQuery.error && !usersQuery.data ? (
          <ErrorState
            title="Unable to load users"
            message={getErrorMessage(usersQuery.error, "Unable to load users.")}
          />
        ) : (
          <DataTable
            columns={userColumns}
            data={users}
            loading={usersQuery.isLoading}
            rowKey={(row) => row.id}
            empty={needle ? "No users match your search" : "No users yet"}
            emptyDescription={needle ? "Try a different name, email or role." : "Create the first user with the form above."}
            emptyIcon={Users}
          />
        )}
      </section>
    </div>
  );
}
