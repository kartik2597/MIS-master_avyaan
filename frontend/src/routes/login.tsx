import { createFileRoute, redirect } from "@tanstack/react-router";
import { authStore } from "@/app/store/authStore";
import { AuthLayout } from "@/layouts/AuthLayout";
import { LoginPage } from "@/modules/auth/pages/LoginPage";

export const Route = createFileRoute("/login")({
  // Needs the browser's stored session to know if someone is already signed in.
  ssr: false,
  beforeLoad: () => {
    if (authStore.isAuthenticated()) {
      throw redirect({ to: "/dashboard/agent" });
    }
  },
  head: () => ({ meta: [{ title: "Sign in · MIS Master 2.0" }] }),
  component: LoginRoute,
});

function LoginRoute() {
  return (
    <AuthLayout>
      <LoginPage />
    </AuthLayout>
  );
}
