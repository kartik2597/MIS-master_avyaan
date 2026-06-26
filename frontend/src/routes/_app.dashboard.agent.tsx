import { createFileRoute } from "@tanstack/react-router";
import { AgentDashboard } from "@/modules/dashboard/agent/pages/AgentDashboard";

export const Route = createFileRoute("/_app/dashboard/agent")({
  head: () => ({ meta: [{ title: "Agent Dashboard · MIS Master" }] }),
  component: AgentDashboard,
});
