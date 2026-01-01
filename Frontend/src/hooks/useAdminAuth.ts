import { useState, useEffect } from "react";
import { useUserAuth } from "./useUserAuth";
import { authFetch } from "@/lib/api";

export interface AdminAuth {
  isAdmin: boolean;
  isLoading: boolean;
}

/**
 * Hook to check if the current user is an admin.
 * Makes a lightweight API call to verify admin status.
 */
export function useAdminAuth(): AdminAuth {
  const { isAuthenticated, userId } = useUserAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function checkAdminStatus() {
      if (!isAuthenticated || !userId) {
        setIsAdmin(false);
        setIsLoading(false);
        return;
      }

      try {
        // Try to call an admin endpoint - if it succeeds, user is admin
        // We use a lightweight endpoint that doesn't require much data
        await authFetch("/api/v1/admin/metrics/location_states");
        setIsAdmin(true);
      } catch (err: any) {
        // If we get 401/403, user is not admin
        if (err?.message?.includes("401") || err?.message?.includes("403") || err?.message?.includes("forbidden")) {
          setIsAdmin(false);
        } else {
          // For other errors, assume not admin to be safe
          setIsAdmin(false);
        }
      } finally {
        setIsLoading(false);
      }
    }

    checkAdminStatus();
  }, [isAuthenticated, userId]);

  return { isAdmin, isLoading };
}




