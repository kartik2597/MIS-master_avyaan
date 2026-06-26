import { Link, useNavigate, useRouterState, Outlet } from "@tanstack/react-router";
import { useAuth, authStore } from "@/app/store/authStore";
import { filterNavByRole, NAV_ITEMS } from "@/shared/constants/navigation";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LogOut, Menu, User as UserIcon, BarChart3 } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase();
}

export function MainLayout() {
  const { user, hydrated } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (hydrated && !user) {
      window.location.replace("/login");
    }
  }, [hydrated, user]);

  if (!hydrated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-sm text-muted-foreground">Loading workspace...</div>
      </div>
    );
  }

  const navItems = filterNavByRole(NAV_ITEMS, user.role);

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:sticky inset-y-0 left-0 z-40 w-64 bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col transition-transform top-0 h-screen",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <div className="h-16 flex items-center gap-2 px-5 border-b border-sidebar-border">
          <div className="h-9 w-9 rounded-lg bg-sidebar-primary flex items-center justify-center">
            <BarChart3 className="h-5 w-5 text-sidebar-primary-foreground" />
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">MIS Master</p>
            <p className="text-[10px] uppercase tracking-widest text-sidebar-foreground/60">v2.0</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const hasChildren = item.children && item.children.length > 0;
            const isActive = pathname === item.to || (hasChildren && item.children!.some((c) => c.to === pathname));
            if (hasChildren) {
              return (
                <div key={item.label} className="space-y-0.5">
                  <div className="flex items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                    <Icon className="h-3.5 w-3.5" /> {item.label}
                  </div>
                  {item.children!.map((child) => {
                    const ChildIcon = child.icon;
                    const childActive = pathname === child.to;
                    return (
                      <Link
                        key={child.to}
                        to={child.to}
                        onClick={() => setSidebarOpen(false)}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ml-3",
                          childActive
                            ? "bg-sidebar-primary text-sidebar-primary-foreground font-medium"
                            : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                        )}
                      >
                        <ChildIcon className="h-4 w-4" /> {child.label}
                      </Link>
                    );
                  })}
                </div>
              );
            }
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground font-medium"
                    : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                )}
              >
                <Icon className="h-4 w-4" /> {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-sidebar-border text-xs text-sidebar-foreground/50">
          © 2026 MIS Master
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-20 h-16 bg-card border-b flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen((v) => !v)}>
              <Menu className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-base font-semibold text-foreground">Welcome back, {user.fullName.split(" ")[0]}</h1>
              <p className="text-xs text-muted-foreground">Centralised reporting & operations dashboard</p>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2 h-10">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                    {initials(user.fullName)}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden sm:block text-left leading-tight">
                  <p className="text-sm font-medium">{user.fullName}</p>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{user.role}</p>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="leading-tight">
                  <p className="font-medium">{user.fullName}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate({ to: "/settings" })}>
                <UserIcon className="h-4 w-4 mr-2" /> Profile & Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => {
                  authStore.logout();
                  navigate({ to: "/login" });
                }}
              >
                <LogOut className="h-4 w-4 mr-2" /> Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
