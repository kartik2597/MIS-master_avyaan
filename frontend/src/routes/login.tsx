import { createFileRoute, redirect } from "@tanstack/react-router";
import { AuthLayout } from "@/layouts/AuthLayout";
import { LoginPage } from "@/modules/auth/pages/LoginPage";

export const Route = createFileRoute("/login")({
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
