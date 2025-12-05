import { useState, useEffect, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import AdminSidebar from "./AdminSidebar";
import AdminHeader from "./AdminHeader";
import AdminCommandPalette from "./AdminCommandPalette";
import AdminMobileDrawer from "./AdminMobileDrawer";

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);
  
  // Keyboard shortcut handler for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
      // Close with Escape
      if (e.key === "Escape" && commandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandPaletteOpen]);
  
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar - hidden on mobile initially (will be drawer later) */}
      {!isMobile && (
        <AdminSidebar
          collapsed={sidebarCollapsed}
          onCollapseChange={setSidebarCollapsed}
        />
      )}
      
      {/* Main content area */}
      <div
        className={cn(
          "flex flex-1 flex-col overflow-hidden transition-all duration-300",
          !isMobile && (sidebarCollapsed ? "ml-16" : "ml-64")
        )}
      >
        {/* Header */}
        <AdminHeader onMobileMenuClick={() => setMobileDrawerOpen(true)} />
        
        {/* Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
      
      {/* Mobile Drawer */}
      {isMobile && (
        <AdminMobileDrawer
          open={mobileDrawerOpen}
          onOpenChange={setMobileDrawerOpen}
        />
      )}
      
      {/* Command Palette */}
      <AdminCommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
      />
    </div>
  );
}

