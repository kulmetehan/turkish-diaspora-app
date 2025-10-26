import { useAuth } from "@/hooks/useAuth";
import { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

export default function RequireAdmin({ children }: PropsWithChildren) {
    const { isAuthenticated, isLoading } = useAuth();
    const loc = useLocation();
    // Wait for initial auth hydration to avoid redirecting logged-in users back to /login
    if (isLoading) return null;
    if (!isAuthenticated) return <Navigate to="/login" state={{ from: loc }} replace />;
    return <>{children}</>;
}
// TODO: Optionally check userEmail client-side against a small allowlist for UX only.


