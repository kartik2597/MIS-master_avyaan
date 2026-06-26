import type { Role } from "@/app/store/authStore";
import {
  LayoutDashboard,
  Upload,
  History,
  Users,
  UserCog,
  Settings,
  Activity,
  Headphones,
} from "lucide-react";
import type { ComponentType } from "react";

export interface NavItem {
  label: string;
  to: string;
  icon: ComponentType<{ className?: string }>;
  roles: Role[];
  children?: NavItem[];
}

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    to: "/dashboard/agent",
    icon: LayoutDashboard,
    roles: ["ADMIN", "MIS", "MANAGER"],
    children: [
      { label: "Agent Dashboard", to: "/dashboard/agent", icon: Activity, roles: ["ADMIN", "MIS", "MANAGER"] },
      { label: "Support Dashboard", to: "/dashboard/support", icon: Headphones, roles: ["ADMIN", "MIS", "MANAGER"] },
    ],
  },
  { label: "Upload Reports", to: "/uploads", icon: Upload, roles: ["ADMIN", "MIS"] },
  { label: "Upload History", to: "/upload-history", icon: History, roles: ["ADMIN", "MIS", "MANAGER"] },
  { label: "Employee Master", to: "/employees", icon: Users, roles: ["ADMIN", "MIS"] },
  { label: "User Management", to: "/users", icon: UserCog, roles: ["ADMIN"] },
  { label: "Settings", to: "/settings", icon: Settings, roles: ["ADMIN", "MIS", "MANAGER"] },
];

export function filterNavByRole(items: NavItem[], role: Role): NavItem[] {
  return items
    .filter((i) => i.roles.includes(role))
    .map((i) => ({ ...i, children: i.children ? filterNavByRole(i.children, role) : undefined }));
}
