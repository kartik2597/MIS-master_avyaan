import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { createUser } from "@/services/api/auth";
import type { Role, UserCreatePayload } from "@/services/api/types";

const EMPTY_FORM: UserCreatePayload = {
  full_name: "",
  email: "",
  password: "",
  role: "MIS",
  is_active: true,
};

export function UserManagementPage() {
  const [form, setForm] = useState<UserCreatePayload>(EMPTY_FORM);
  const [createdRole, setCreatedRole] = useState<Role | null>(null);

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: (user) => {
      setCreatedRole(user.role);
      setForm(EMPTY_FORM);
    },
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-xl font-semibold">User Management</h2>
        <p className="text-sm text-muted-foreground">Create backend users with ADMIN, MIS or MANAGER access.</p>
      </div>

      <Card className="p-6">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate(form);
          }}
        >
          <div className="space-y-1.5">
            <Label>Full Name</Label>
            <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label>Password</Label>
            <Input
              type="password"
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select value={form.role} onValueChange={(value) => setForm({ ...form, role: value as Role })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ADMIN">ADMIN</SelectItem>
                <SelectItem value="MIS">MIS</SelectItem>
                <SelectItem value="MANAGER">MANAGER</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create User"}
          </Button>
        </form>
      </Card>

      {createMutation.isSuccess && createdRole && (
        <Badge variant="secondary" className="bg-success/15 text-success">User created as {createdRole}</Badge>
      )}
      {createMutation.error && <p className="text-sm text-destructive">Unable to create user.</p>}
    </div>
  );
}
