import { createFileRoute } from "@tanstack/react-router";
import { UploadsPage } from "@/modules/uploads/pages/UploadsPage";
import { requireNavAccess } from "@/lib/route-guards";

export const Route = createFileRoute("/_app/uploads")({
  beforeLoad: requireNavAccess("/uploads"),
  head: () => ({ meta: [{ title: "Upload Reports · MIS Master" }] }),
  component: UploadsPage,
});
