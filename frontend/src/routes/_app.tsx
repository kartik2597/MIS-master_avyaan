import { createFileRoute, redirect } from "@tanstack/react-router";
import { authStore } from "@/app/store/authStore";
import { MainLayout } from "@/layouts/MainLayout";

export const Route = createFileRoute("/_app")({
  // The session lives in browser storage, which the server cannot see. With SSR on,
  // the server always thought the user was logged out and redirected every hard
  // refresh to /login. Render this layout (and its children) on the client only.
  ssr: false,
  beforeLoad: () => {
    if (!authStore.isAuthenticated()) {
      throw redirect({ to: "/login" });
    }
  },
  component: MainLayout,
});
