import { createFileRoute, redirect } from "@tanstack/react-router";
import { authStore } from "@/app/store/authStore";
import { MainLayout } from "@/layouts/MainLayout";

export const Route = createFileRoute("/_app")({
  beforeLoad: () => {
    if (!authStore.isAuthenticated()) {
      throw redirect({ to: "/login" });
    }
  },
  component: MainLayout,
});
