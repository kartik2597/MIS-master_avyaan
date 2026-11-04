import { createFileRoute } from "@tanstack/react-router";
import { EmployeeMasterPage } from "@/modules/employee-master/pages/EmployeeMasterPage";
import { requireNavAccess } from "@/lib/route-guards";

export const Route = createFileRoute("/_app/employees")({
  beforeLoad: requireNavAccess("/employees"),
  head: () => ({ meta: [{ title: "Employee Master · MIS Master" }] }),
  component: EmployeeMasterPage,
});
