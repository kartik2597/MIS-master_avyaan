import { redirect } from "@tanstack/react-router";
import { authStore } from "@/app/store/authStore";
import { NAV_ITEMS, type NavItem } from "@/shared/constants/navigation";

function findNavItem(items: NavItem[], to: string): NavItem | undefined {
  for (const item of items) {
    if (item.to === to) return item;
    const child = item.children ? findNavItem(item.children, to) : undefined;
    if (child) return child;
  }
  return undefined;
}

/**
 * `beforeLoad` guard that applies the same role rules as the sidebar
 * (see NAV_ITEMS), so typing a URL by hand cannot open a page the role
 * is not meant to see. The parent `_app` route already handles "not logged in".
 * The backend still enforces permissions on every API call; this is the UX layer.
 */
export function requireNavAccess(to: string) {
  return () => {
    const user = authStore.get();
    const item = findNavItem(NAV_ITEMS, to);
    if (!user || !item) return;
    if (!item.roles.includes(user.role)) {
      throw redirect({ to: "/dashboard/agent" });
    }
  };
}
