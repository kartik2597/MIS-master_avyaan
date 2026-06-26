import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/app/store/authStore";

export const Route = createFileRoute("/")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "MIS Master 2.0" },
      { name: "description", content: "Centralised reporting and dashboard platform for Agent & Support operations." },
    ],
  }),
  component: IndexRedirect,
});

function IndexRedirect() {
  const { user, hydrated } = useAuth();

  useEffect(() => {
    if (!hydrated) return;
    const target = user ? "/dashboard/agent" : "/login";
    window.location.replace(target);
  }, [hydrated, user]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-sm text-muted-foreground">Loading MIS Master...</div>
    </div>
  );
}
