import { ReactNode } from "react";
import RequireAdmin from "@/components/auth/RequireAdmin";
import AdminLayout from "./AdminLayout";

interface AdminRouteWrapperProps {
  children: ReactNode;
}

/**
 * Wrapper component that combines authentication check and admin layout
 * Use this for all admin routes
 */
export default function AdminRouteWrapper({ children }: AdminRouteWrapperProps) {
  return (
    <RequireAdmin>
      <AdminLayout>
        {children}
      </AdminLayout>
    </RequireAdmin>
  );
}





























