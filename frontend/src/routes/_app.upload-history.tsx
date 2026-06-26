import { createFileRoute } from "@tanstack/react-router";
import { UploadHistoryPage } from "@/modules/upload-history/pages/UploadHistoryPage";

export const Route = createFileRoute("/_app/upload-history")({
  head: () => ({ meta: [{ title: "Upload History · MIS Master" }] }),
  component: UploadHistoryPage,
});
