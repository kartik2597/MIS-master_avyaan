import type { ComponentType, ReactNode } from "react";
import { EmptyIllustration } from "@/shared/components/Art/Art";

interface EmptyStateProps {
  title: string;
  description?: string;
  /** Pass an icon for a compact state. Without one, the empty-state illustration is shown. */
  icon?: ComponentType<{ className?: string }>;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon: Icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 px-4 text-center">
      {Icon ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
      ) : (
        <EmptyIllustration className="h-28 w-auto" />
      )}
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="text-sm text-muted-foreground max-w-sm">{description}</p>}
      </div>
      {action}
    </div>
  );
}
