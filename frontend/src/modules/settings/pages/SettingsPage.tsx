import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { PageHeader } from "@/shared/components/PageHeader/PageHeader";
import { StatusBadge } from "@/shared/components/StatusBadge/StatusBadge";
import { useAuth } from "@/app/store/authStore";
import { setThemePreference, useThemePreference, type ThemePreference } from "@/lib/theme";
import { ChangePasswordCard } from "@/modules/settings/components/ChangePasswordCard";
import { cn } from "@/lib/utils";
import { Check, CheckCircle2, Monitor, Moon, Sun } from "lucide-react";

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const THEME_OPTIONS: { value: ThemePreference; label: string; hint: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", hint: "Bright and clear", icon: Sun },
  { value: "dark", label: "Dark", hint: "Easy on the eyes", icon: Moon },
  { value: "system", label: "System", hint: "Match this device", icon: Monitor },
];

/** What each role can do in the app. Mirrors the sidebar menu and the edit rights on each page. */
const ROLE_ACCESS: Record<string, string[]> = {
  ADMIN: [
    "View the dashboards and upload history",
    "Upload and process report files",
    "Add, edit and delete employees and uploads",
    "Create users and choose their access level",
  ],
  MIS: [
    "View the dashboards and upload history",
    "Upload and process report files",
    "Add, edit and delete employees and uploads",
  ],
  MANAGER: ["View the dashboards", "View the upload history"],
  TL: ["View the dashboards", "View the upload history"],
};

export function SettingsPage() {
  const { user } = useAuth();
  const theme = useThemePreference();
  const access = ROLE_ACCESS[user?.role ?? ""] ?? [];

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader title="Settings" description="Your profile, appearance and access in MIS Master." />

      <Card className="shadow-card overflow-hidden">
        <div className="flex items-center gap-4 p-6 border-b bg-muted/30">
          <Avatar className="h-14 w-14">
            <AvatarFallback className="bg-primary text-primary-foreground text-lg font-semibold">
              {initials(user?.fullName ?? "")}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 space-y-1.5">
            <p className="text-lg font-semibold leading-tight truncate">{user?.fullName ?? "-"}</p>
            <StatusBadge label={user?.role ?? "Unknown"} tone="info" />
          </div>
        </div>

        <div className="p-6 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Profile details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="profile-name">Full Name</Label>
              <Input id="profile-name" value={user?.fullName ?? ""} disabled />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="profile-email">Email</Label>
              <Input id="profile-email" type="email" value={user?.email ?? ""} disabled />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="profile-role">Role</Label>
              <Input id="profile-role" value={user?.role ?? ""} disabled />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Profile details are read-only. Contact an administrator to change them.
          </p>
        </div>
      </Card>

      <Card className="p-6 shadow-card space-y-4">
        <div className="space-y-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Appearance</h3>
          <p className="text-sm text-muted-foreground">Choose how MIS Master looks on this device.</p>
        </div>
        <div role="radiogroup" aria-label="Colour theme" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {THEME_OPTIONS.map(({ value, label, hint, icon: Icon }) => {
            const selected = theme === value;
            return (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setThemePreference(value)}
                className={cn(
                  "relative flex items-center gap-3 rounded-lg border p-3 text-left transition-colors",
                  selected ? "border-primary bg-primary/5 ring-1 ring-primary" : "hover:bg-muted/50",
                )}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-md",
                    selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 leading-tight">
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">{hint}</p>
                </div>
                {selected && <Check className="absolute right-3 top-3 h-4 w-4 text-primary" />}
              </button>
            );
          })}
        </div>
      </Card>

      <ChangePasswordCard />

      {access.length > 0 && (
        <Card className="p-6 shadow-card space-y-4">
          <div className="space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Your access</h3>
            <p className="text-sm text-muted-foreground">What you can do with the {user?.role} role.</p>
          </div>
          <ul className="space-y-2.5">
            {access.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                {item}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
