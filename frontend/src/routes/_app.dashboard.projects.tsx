import { createFileRoute } from "@tanstack/react-router";
import { ProjectDashboard } from "@/modules/dashboard/projects/pages/ProjectDashboard";

export const Route = createFileRoute("/_app/dashboard/projects")({
  head: () => ({ meta: [{ title: "Project & Timesheet · MIS Master" }] }),
  component: ProjectDashboard,
});
