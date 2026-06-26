import { createFileRoute } from "@tanstack/react-router";
import { SupportDashboard } from "@/modules/dashboard/support/pages/SupportDashboard";

export const Route = createFileRoute("/_app/dashboard/support")({
  head: () => ({ meta: [{ title: "Support Dashboard · MIS Master" }] }),
  component: SupportDashboard,
});
