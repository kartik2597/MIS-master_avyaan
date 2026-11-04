import { createFileRoute } from "@tanstack/react-router";
import { HiringDashboard } from "@/modules/dashboard/hiring/pages/HiringDashboard";

export const Route = createFileRoute("/_app/dashboard/hiring")({
  head: () => ({ meta: [{ title: "Hiring & Attrition · MIS Master" }] }),
  component: HiringDashboard,
});
