import { useState, useEffect } from "react";
import { Drawer } from "vaul";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { adminNavigation } from "@/lib/admin/navigation";
import AdminSidebarNavGroup from "./AdminSidebarNavGroup";

interface AdminMobileDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function AdminMobileDrawer({ open, onOpenChange }: AdminMobileDrawerProps) {
  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange} direction="left">
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Drawer.Content className="fixed inset-y-0 left-0 w-64 bg-background border-r z-50 flex flex-col">
          <div className="flex h-16 items-center justify-between border-b px-4">
            <h2 className="text-lg font-semibold">Admin</h2>
            <Drawer.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close navigation menu">
                <Icon name="X" sizeRem={1.25} />
              </Button>
            </Drawer.Close>
          </div>
          
          <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Admin navigation">
            <div className="space-y-6">
              {adminNavigation.map((group) => (
                <AdminSidebarNavGroup 
                  key={group.id} 
                  group={group} 
                  collapsed={false}
                />
              ))}
            </div>
          </nav>
          
          <div className="border-t p-4 text-xs text-muted-foreground">
            Turkish Diaspora App
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}

