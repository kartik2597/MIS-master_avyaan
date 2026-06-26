import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/app/store/authStore";

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-semibold">Settings</h2>
        <p className="text-sm text-muted-foreground">Authenticated profile details from the backend.</p>
      </div>

      <Card className="p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Full Name</Label>
            <Input value={user?.fullName ?? ""} disabled />
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input type="email" value={user?.email ?? ""} disabled />
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Input value={user?.role ?? ""} disabled />
          </div>
        </div>
      </Card>
    </div>
  );
}
