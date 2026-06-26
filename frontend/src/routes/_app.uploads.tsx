import { createFileRoute } from "@tanstack/react-router";
import { UploadsPage } from "@/modules/uploads/pages/UploadsPage";

export const Route = createFileRoute("/_app/uploads")({
  head: () => ({ meta: [{ title: "Upload Reports · MIS Master" }] }),
  component: UploadsPage,
});
