import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/modules/settings/pages/SettingsPage";

export const Route = createFileRoute("/_app/settings")({
  head: () => ({ meta: [{ title: "Settings · MIS Master" }] }),
  component: SettingsPage,
});
