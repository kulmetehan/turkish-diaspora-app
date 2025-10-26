import { useAuth } from "@/hooks/useAuth";
import { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

export default function RequireAdmin({ children }: PropsWithChildren) {
    const { isAuthenticated } = useAuth();
    const loc = useLocation();
    if (!isAuthenticated) return <Navigate to="/login" state={{ from: loc }} replace />;
    return <>{children}</>;
}
// TODO: Optionally check userEmail client-side against a small allowlist for UX only.


