import { createFileRoute } from "@tanstack/react-router";
import { UserManagementPage } from "@/modules/user-management/pages/UserManagementPage";

export const Route = createFileRoute("/_app/users")({
  head: () => ({ meta: [{ title: "User Management · MIS Master" }] }),
  component: UserManagementPage,
});
