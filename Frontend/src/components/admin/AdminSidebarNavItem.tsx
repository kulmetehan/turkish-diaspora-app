import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { useLocation, Link } from "react-router-dom";
import type { NavItem } from "@/lib/admin/navigation";

interface AdminSidebarNavItemProps {
  item: NavItem;
  collapsed?: boolean;
}

export default function AdminSidebarNavItem({ item, collapsed = false }: AdminSidebarNavItemProps) {
  const location = useLocation();
  const isActive = location.pathname === item.path || 
    (item.path !== "/admin" && location.pathname.startsWith(item.path));
  
  return (
    <Link
      to={item.path}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        "hover:bg-accent hover:text-accent-foreground",
        isActive && "bg-accent text-accent-foreground",
        collapsed && "justify-center px-2"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon 
        name={item.icon} 
        sizeRem={1.25} 
        className={cn(
          "flex-shrink-0",
          isActive && "text-primary"
        )}
        decorative={false}
        title={item.label}
      />
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge && (
            <span className={cn(
              "flex h-5 items-center rounded-full px-2 text-xs font-medium",
              typeof item.badge === "string" 
                ? "bg-muted text-muted-foreground"
                : "bg-primary text-primary-foreground"
            )}>
              {item.badge}
            </span>
          )}
        </>
      )}
    </Link>
  );
}










