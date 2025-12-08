import * as React from "react";
import * as Collapsible from "@radix-ui/react-collapsible";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { useLocation } from "react-router-dom";
import type { NavGroup } from "@/lib/admin/navigation";
import AdminSidebarNavItem from "./AdminSidebarNavItem";

interface AdminSidebarNavGroupProps {
  group: NavGroup;
  collapsed?: boolean;
}

export default function AdminSidebarNavGroup({ group, collapsed = false }: AdminSidebarNavGroupProps) {
  const location = useLocation();
  const [open, setOpen] = React.useState(true);
  
  // Check if any item in this group is active to auto-expand
  const hasActiveItem = group.items.some(
    (item) => location.pathname === item.path || 
      (item.path !== "/admin" && location.pathname.startsWith(item.path))
  );
  
  React.useEffect(() => {
    if (hasActiveItem) {
      setOpen(true);
    }
  }, [hasActiveItem]);
  
  // If collapsed, just show items without group header
  if (collapsed) {
    return (
      <div className="space-y-1">
        {group.items.map((item) => (
          <AdminSidebarNavItem key={item.id} item={item} collapsed={collapsed} />
        ))}
      </div>
    );
  }
  
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="space-y-1">
      <Collapsible.Trigger
        className={cn(
          "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-semibold text-muted-foreground",
          "hover:bg-accent hover:text-accent-foreground transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        )}
      >
        <span className="uppercase tracking-wider text-xs">{group.label}</span>
        <Icon
          name="ChevronDown"
          sizeRem={1}
          className={cn(
            "transition-transform duration-200",
            !open && "-rotate-90"
          )}
        />
      </Collapsible.Trigger>
      <Collapsible.Content className="space-y-1 data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        {group.items.map((item) => (
          <AdminSidebarNavItem key={item.id} item={item} collapsed={collapsed} />
        ))}
      </Collapsible.Content>
    </Collapsible.Root>
  );
}











