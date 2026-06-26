import { createFileRoute } from "@tanstack/react-router";
import { EmployeeMasterPage } from "@/modules/employee-master/pages/EmployeeMasterPage";

export const Route = createFileRoute("/_app/employees")({
  head: () => ({ meta: [{ title: "Employee Master · MIS Master" }] }),
  component: EmployeeMasterPage,
});
