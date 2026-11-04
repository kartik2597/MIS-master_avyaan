import { FileSpreadsheet, Gauge, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { ThemeToggle } from "@/shared/components/ThemeToggle/ThemeToggle";
import { BrandMark, HeroIllustration } from "@/shared/components/Art/Art";

const FEATURES = [
  {
    icon: FileSpreadsheet,
    title: "Upload once",
    text: "Drop APR, adherence, shrinkage or master files. The report type is detected for you.",
  },
  {
    icon: ShieldCheck,
    title: "Validated automatically",
    text: "Required columns are checked before anything reaches the database.",
  },
  {
    icon: Gauge,
    title: "Live KPIs",
    text: "Headcount, adherence, shrinkage and time utilisation in one dashboard.",
  },
];

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-[1.05fr_1fr] bg-background">
      {/* Brand panel */}
      <div className="hidden lg:flex bg-sidebar text-sidebar-foreground p-12 xl:p-16 flex-col justify-between relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-60 [mask-image:radial-gradient(ellipse_at_top_left,black,transparent_70%)]" />
        <div className="absolute -top-40 -right-40 h-[26rem] w-[26rem] rounded-full bg-sidebar-primary/15 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <BrandMark className="h-10 w-10 rounded-lg shadow-lg shadow-black/20" />
          <div className="leading-tight">
            <p className="font-semibold tracking-tight">MIS Master</p>
            <p className="text-xs text-sidebar-foreground/55">Reporting suite</p>
          </div>
        </div>

        <div className="relative space-y-8 max-w-lg">
          <div className="space-y-4">
            <h2 className="text-4xl font-semibold leading-tight tracking-tight">
              Every report, one <span className="text-sidebar-primary">clear picture</span> of your floor.
            </h2>
            <p className="text-sidebar-foreground/70 leading-relaxed">
              Centralised reporting for call-centre operations: upload, validate and monitor agent performance
              without the spreadsheet juggling.
            </p>
          </div>

          {/* Illustration of the dashboard. The figures are decorative, not real data. */}
          <HeroIllustration className="w-full h-auto drop-shadow-2xl" />

          <ul className="space-y-1">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <li
                key={title}
                className="group flex gap-4 rounded-lg p-3 -mx-3 transition-colors hover:bg-sidebar-accent/40"
              >
                <div className="h-9 w-9 shrink-0 rounded-md bg-sidebar-accent/70 border border-sidebar-border flex items-center justify-center">
                  <Icon className="h-4 w-4 text-sidebar-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">{title}</p>
                  <p className="text-sm text-sidebar-foreground/65 leading-relaxed">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-sidebar-foreground/50">© 2026 MIS Master</p>
      </div>

      {/* Form panel */}
      <div className="relative flex flex-col items-center justify-center p-4 sm:p-6 gap-8 bg-muted/40">
        <ThemeToggle className="absolute right-4 top-4" />
        <div className="flex items-center gap-2.5 lg:hidden">
          <BrandMark className="h-9 w-9 rounded-lg" />
          <p className="font-semibold tracking-tight">MIS Master</p>
        </div>
        <div className="w-full flex justify-center">{children}</div>
      </div>
    </div>
  );
}
