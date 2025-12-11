import { useState, useEffect } from "react";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { adminNavigation } from "@/lib/admin/navigation";
import AdminSidebarNavGroup from "./AdminSidebarNavGroup";

interface AdminSidebarProps {
  collapsed?: boolean;
  onCollapseChange?: (collapsed: boolean) => void;
}

export default function AdminSidebar({ collapsed: controlledCollapsed, onCollapseChange }: AdminSidebarProps) {
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  
  const collapsed = controlledCollapsed ?? internalCollapsed;
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);
  
  const handleToggle = () => {
    const newCollapsed = !collapsed;
    if (onCollapseChange) {
      onCollapseChange(newCollapsed);
    } else {
      setInternalCollapsed(newCollapsed);
    }
  };
  
  // On mobile, sidebar is hidden by default (handled by drawer)
  if (isMobile) {
    return null;
  }
  
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen border-r bg-background transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
      aria-label="Admin navigation"
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          {!collapsed && (
            <h2 className="text-lg font-semibold">Admin</h2>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggle}
            className="ml-auto"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icon 
              name={collapsed ? "ChevronRight" : "ChevronLeft"} 
              sizeRem={1.25}
            />
          </Button>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Admin navigation">
          <div className="space-y-6">
            {adminNavigation.map((group) => (
              <AdminSidebarNavGroup 
                key={group.id} 
                group={group} 
                collapsed={collapsed}
              />
            ))}
          </div>
        </nav>
        
        {/* Footer */}
        {!collapsed && (
          <div className="border-t p-4 text-xs text-muted-foreground">
            Turkish Diaspora App
          </div>
        )}
      </div>
    </aside>
  );
}













