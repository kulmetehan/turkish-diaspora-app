/**
 * Admin Navigation Configuration
 * 
 * Defines the navigation structure for the admin sidebar.
 * Each item represents a route with its icon, label, and optional children.
 */

export type LucideIcon = keyof typeof import("lucide-react");

export interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  path: string;
  badge?: number | string;
  children?: NavItem[];
  group?: string;
}

export interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

/**
 * Complete navigation structure for admin sidebar
 */
export const adminNavigation: NavGroup[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    items: [
      {
        id: "overview",
        label: "Overview",
        icon: "LayoutDashboard",
        path: "/admin",
        group: "dashboard",
      },
      {
        id: "locations",
        label: "Locations",
        icon: "MapPin",
        path: "/admin/locations",
        group: "dashboard",
      },
      {
        id: "metrics",
        label: "Metrics",
        icon: "BarChart3",
        path: "/admin/metrics",
        group: "dashboard",
      },
      {
        id: "discovery",
        label: "Discovery Coverage",
        icon: "Map",
        path: "/admin/discovery",
        group: "dashboard",
      },
      {
        id: "ai-policy",
        label: "AI Policy",
        icon: "Brain",
        path: "/admin/settings/ai-policy",
        group: "dashboard",
      },
      {
        id: "tasks",
        label: "Tasks",
        icon: "CheckSquare",
        path: "/admin/tasks",
        group: "dashboard",
      },
      {
        id: "news-ai",
        label: "News AI Logs",
        icon: "Newspaper",
        path: "/admin/news-ai",
        group: "dashboard",
      },
      {
        id: "authenticated-claims",
        label: "Claims",
        icon: "FileCheck",
        path: "/admin/authenticated-claims",
        group: "dashboard",
      },
      {
        id: "outreach-contacts",
        label: "Outreach Contacts",
        icon: "Mail",
        path: "/admin/outreach-contacts",
        group: "dashboard",
      },
    ],
  },
  {
    id: "configuration",
    label: "Configuration",
    items: [
      {
        id: "cities",
        label: "Cities",
        icon: "Building2",
        path: "/admin/cities",
        group: "configuration",
      },
      {
        id: "event-sources",
        label: "Event Sources",
        icon: "Rss",
        path: "/admin/event-sources",
        group: "configuration",
      },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      {
        id: "workers",
        label: "Workers",
        icon: "Cog",
        path: "/admin/workers",
        group: "operations",
      },
    ],
  },
  {
    id: "events",
    label: "Events",
    items: [
      {
        id: "events-dashboard",
        label: "Events Dashboard",
        icon: "Calendar",
        path: "/admin/events",
        group: "events",
      },
      {
        id: "polls",
        label: "Polls",
        icon: "MessageSquare",
        path: "/admin/polls",
        group: "events",
      },
    ],
  },
  {
    id: "moderation",
    label: "Moderation",
    items: [
      {
        id: "reports",
        label: "Reports",
        icon: "Flag",
        path: "/admin/reports",
        group: "moderation",
      },
      {
        id: "bulletin",
        label: "Bulletin Moderation",
        icon: "MessageSquare",
        path: "/admin/bulletin",
        group: "moderation",
      },
    ],
  },
  {
    id: "system",
    label: "System",
    items: [
      {
        id: "audit",
        label: "Audit Log",
        icon: "FileText",
        path: "/admin/audit",
        group: "system",
        badge: "coming soon",
      },
    ],
  },
];

/**
 * Flattened list of all navigation items for easy lookup
 */
export const allNavItems: NavItem[] = adminNavigation.flatMap((group) => group.items);

/**
 * Find a navigation item by path
 */
export function findNavItemByPath(path: string): NavItem | undefined {
  return allNavItems.find((item) => item.path === path);
}

/**
 * Find navigation items matching a path prefix (for breadcrumbs)
 */
export function findNavItemsByPathPrefix(path: string): NavItem[] {
  return allNavItems.filter((item) => path.startsWith(item.path));
}

/**
 * Get navigation group for a given item
 */
export function getNavGroupForItem(item: NavItem): NavGroup | undefined {
  return adminNavigation.find((group) => group.items.some((i) => i.id === item.id));
}





