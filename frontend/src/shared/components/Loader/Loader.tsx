import { Loader2 } from "lucide-react";

export function Loader({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
      <Loader2 className="h-6 w-6 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
