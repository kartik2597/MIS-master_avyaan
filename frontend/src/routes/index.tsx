import { createFileRoute, redirect } from "@tanstack/react-router";
import { authStore } from "@/app/store/authStore";

export const Route = createFileRoute("/")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "MIS Master" },
      { name: "description", content: "Centralised reporting and dashboard platform for Agent & Support operations." },
    ],
  }),
  // Redirect through the router (no full page reload) before anything renders.
  beforeLoad: () => {
    throw redirect({ to: authStore.isAuthenticated() ? "/dashboard/agent" : "/login" });
  },
  component: () => null,
});
