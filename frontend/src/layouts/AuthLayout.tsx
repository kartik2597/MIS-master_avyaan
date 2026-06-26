import { BarChart3 } from "lucide-react";
import type { ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="hidden lg:flex bg-sidebar text-sidebar-foreground p-12 flex-col justify-between relative overflow-hidden">
        <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-sidebar-primary/30 blur-3xl" />
        <div className="absolute -bottom-32 -left-20 h-80 w-80 rounded-full bg-info/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-sidebar-primary flex items-center justify-center">
            <BarChart3 className="h-6 w-6 text-sidebar-primary-foreground" />
          </div>
          <div>
            <p className="font-semibold">MIS Master</p>
            <p className="text-xs text-sidebar-foreground/60 uppercase tracking-widest">v2.0</p>
          </div>
        </div>
        <div className="relative space-y-4 max-w-md">
          <h2 className="text-3xl font-semibold leading-tight">
            Centralised reporting for Agent & Support operations.
          </h2>
          <p className="text-sidebar-foreground/70">
            Upload reports, automate validations, and monitor real-time KPIs across adherence,
            shrinkage, productivity, and attendance — all from one workspace.
          </p>
          <div className="grid grid-cols-3 gap-4 pt-6">
            {[
              { k: "12+", v: "KPIs tracked" },
              { k: "3", v: "User roles" },
              { k: "100%", v: "Mock-ready" },
            ].map((s) => (
              <div key={s.v} className="rounded-lg bg-sidebar-accent/50 p-3">
                <p className="text-xl font-semibold">{s.k}</p>
                <p className="text-xs text-sidebar-foreground/70">{s.v}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-sidebar-foreground/50">© 2026 MIS Master 2.O</p>
      </div>
      <div className="flex items-center justify-center p-6">{children}</div>
    </div>
  );
}
