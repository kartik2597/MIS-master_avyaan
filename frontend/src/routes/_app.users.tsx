import { createFileRoute } from "@tanstack/react-router";
import { UserManagementPage } from "@/modules/user-management/pages/UserManagementPage";
import { requireNavAccess } from "@/lib/route-guards";

export const Route = createFileRoute("/_app/users")({
  beforeLoad: requireNavAccess("/users"),
  head: () => ({ meta: [{ title: "User Management · MIS Master" }] }),
  component: UserManagementPage,
});
