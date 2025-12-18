import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/lib/supabaseClient";

export default function AdminUserMenu() {
  const { userEmail } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);
  
  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/login");
  };
  
  if (!userEmail) {
    return null;
  }
  
  // Get initials from email
  const initials = userEmail
    .split("@")[0]
    .split(".")
    .map((part) => part.charAt(0).toUpperCase())
    .slice(0, 2)
    .join("") || "A";
  
  return (
    <div className="relative" ref={menuRef}>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen(!open)}
        className="h-9 w-9 rounded-full"
        aria-label="User menu"
        aria-expanded={open}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-medium">
          {initials}
        </div>
      </Button>
      
      {open && (
        <div
          className={cn(
            "absolute right-0 top-full mt-2 z-50 min-w-[200px] rounded-md border bg-background shadow-lg",
            "animate-scale-in"
          )}
          role="menu"
          aria-orientation="vertical"
        >
          <div className="p-2">
            <div className="px-3 py-2 text-sm font-medium border-b">
              {userEmail}
            </div>
            <button
              onClick={handleLogout}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 text-sm text-left",
                "hover:bg-accent hover:text-accent-foreground rounded-sm",
                "transition-colors"
              )}
              role="menuitem"
            >
              <Icon name="LogOut" sizeRem={1} />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
}























