import { Link, useNavigate, useRouterState, Outlet } from "@tanstack/react-router";
import { useAuth, authStore } from "@/app/store/authStore";
import { filterNavByRole, NAV_ITEMS, type NavItem } from "@/shared/constants/navigation";
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
import { ChevronDown, LogOut, Menu, User as UserIcon, X } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/shared/components/ThemeToggle/ThemeToggle";
import { BrandMark } from "@/shared/components/Art/Art";

const SIDEBAR_STORAGE_KEY = "mis-sidebar-collapsed";

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

/** Finds the section and page names for the current URL, e.g. "Dashboard" / "Agent Dashboard". */
function findCrumbs(items: NavItem[], pathname: string): string[] {
  for (const item of items) {
    const child = item.children?.find((c) => c.to === pathname);
    if (child) return [item.label, child.label];
    if (item.to === pathname) return [item.label];
  }
  return [];
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-3 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/45">
      {children}
    </p>
  );
}

function SidebarLink({
  to,
  label,
  icon: Icon,
  active,
  onNavigate,
}: {
  to: string;
  label: string;
  icon: NavItem["icon"];
  active: boolean;
  onNavigate: () => void;
}) {
  return (
    <Link
      to={to}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
        active
          ? "bg-sidebar-primary font-medium text-sidebar-primary-foreground shadow-sm"
          : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
      )}
    >
      {active && <span className="absolute -left-3 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-sidebar-foreground" />}
      <span
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
          active ? "bg-white/15" : "bg-sidebar-accent/60 group-hover:bg-sidebar-accent",
        )}
      >
        <Icon className="h-4 w-4" />
      </span>
      <span className="truncate">{label}</span>
    </Link>
  );
}

export function MainLayout() {
  const { user, hydrated } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  // Mobile: the drawer is open. Desktop: the sidebar is slid out of view.
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // Restore the desktop choice after mount (kept out of the first render so server and browser markup match).
  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1");
    } catch {
      // Storage blocked: start expanded.
    }
  }, []);

  function toggleSidebar() {
    if (window.matchMedia("(min-width: 1024px)").matches) {
      const next = !collapsed;
      setCollapsed(next);
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // The choice still applies for this visit.
      }
    } else {
      setSidebarOpen((v) => !v);
    }
  }

  useEffect(() => {
    if (hydrated && !user) {
      navigate({ to: "/login", replace: true });
    }
  }, [hydrated, user, navigate]);

  // Name the browser tab after the page, so several open tabs are easy to tell apart.
  useEffect(() => {
    if (!user) return;
    const names = findCrumbs(filterNavByRole(NAV_ITEMS, user.role), pathname);
    const page = names[names.length - 1];
    document.title = page ? `${page} · MIS Master` : "MIS Master";
  }, [user, pathname]);

  // Close the mobile drawer on Escape.
  useEffect(() => {
    if (!sidebarOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setSidebarOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen]);

  if (!hydrated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" role="status">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <BrandMark className="h-10 w-10 rounded-lg animate-pulse" />
          <p className="text-sm">Loading workspace...</p>
        </div>
      </div>
    );
  }

  const navItems = filterNavByRole(NAV_ITEMS, user.role);
  const crumbs = findCrumbs(navItems, pathname);
  const pageTitle = crumbs[crumbs.length - 1] ?? "MIS Master";
  const closeDrawer = () => setSidebarOpen(false);

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside
        aria-label="Primary navigation"
        className={cn(
          "fixed lg:sticky inset-y-0 left-0 z-40 w-64 bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col overflow-hidden transition-[margin,transform,visibility] duration-200 top-0 h-screen",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          collapsed && "lg:-ml-64 lg:invisible",
        )}
      >
        <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-sidebar-primary/10 to-transparent" />

        <div className="relative h-16 flex items-center justify-between gap-2 px-4 border-b border-sidebar-border">
          <div className="flex items-center gap-3">
            <BrandMark className="h-9 w-9 rounded-lg shadow-md shadow-black/20" />
            <div className="leading-tight">
              <p className="font-semibold text-sm tracking-tight">MIS Master</p>
              <p className="text-[11px] text-sidebar-foreground/50">Reporting suite</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            onClick={closeDrawer}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="relative flex-1 overflow-y-auto p-3 space-y-0.5">
          {navItems.map((item, index) => {
            const hasChildren = !!item.children && item.children.length > 0;
            const previous = navItems[index - 1];
            const previousIsGroup = !!previous && !!previous.children && previous.children.length > 0;
            // One "Workspace" label above each run of single links.
            const showWorkspaceLabel = !hasChildren && (index === 0 || previousIsGroup);

            if (hasChildren) {
              return (
                <div key={item.label} className="space-y-0.5">
                  <SectionLabel>{item.label}</SectionLabel>
                  {item.children!.map((child) => (
                    <SidebarLink
                      key={child.to}
                      to={child.to}
                      label={child.label}
                      icon={child.icon}
                      active={pathname === child.to}
                      onNavigate={closeDrawer}
                    />
                  ))}
                </div>
              );
            }
            return (
              <div key={item.to} className="space-y-0.5">
                {showWorkspaceLabel && <SectionLabel>Workspace</SectionLabel>}
                <SidebarLink
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  active={pathname === item.to}
                  onNavigate={closeDrawer}
                />
              </div>
            );
          })}
        </nav>

        <div className="relative p-3 border-t border-sidebar-border">
          <div className="flex items-center gap-3 rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-2.5">
            <div className="relative shrink-0">
              <Avatar className="h-9 w-9">
                <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground text-xs font-semibold">
                  {initials(user.fullName)}
                </AvatarFallback>
              </Avatar>
              <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-success ring-2 ring-sidebar" />
            </div>
            <div className="min-w-0 flex-1 leading-tight">
              <p className="text-sm font-medium truncate">{user.fullName}</p>
              <p className="text-[10px] uppercase tracking-wider text-sidebar-foreground/55">{user.role}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              onClick={() => {
                authStore.logout();
              }}
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-[1px] z-30 lg:hidden"
          onClick={closeDrawer}
          aria-hidden="true"
        />
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-20 h-16 bg-card/80 backdrop-blur border-b flex items-center justify-between px-4 lg:px-8">
          <div className="flex items-center gap-3 min-w-0">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              aria-label="Toggle navigation"
              aria-expanded={sidebarOpen || !collapsed}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0 leading-tight">
              {crumbs.length > 1 && (
                <p className="text-xs text-muted-foreground truncate">{crumbs.slice(0, -1).join(" / ")}</p>
              )}
              <h1 className="text-base font-semibold text-foreground truncate">{pageTitle}</h1>
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
          <ThemeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2 h-10 px-2">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                    {initials(user.fullName)}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden sm:block text-left leading-tight">
                  <p className="text-sm font-medium">{user.fullName}</p>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{user.role}</p>
                </div>
                <ChevronDown className="hidden sm:block h-4 w-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="leading-tight">
                  <p className="font-medium">{user.fullName}</p>
                  <p className="text-xs font-normal text-muted-foreground">{user.email}</p>
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
                }}
              >
                <LogOut className="h-4 w-4 mr-2" /> Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-8">
          <div className="mx-auto w-full max-w-7xl">
            {/* Keyed by path so every page change plays the short fade-in. */}
            <div key={pathname} className="animate-in fade-in slide-in-from-bottom-1 duration-300">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
