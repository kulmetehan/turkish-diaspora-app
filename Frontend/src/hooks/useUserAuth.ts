// Frontend/src/hooks/useUserAuth.ts
import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState, useRef } from "react";
import { identifyUser, resetUser } from "@/lib/analytics";

export interface UserAuth {
  userId: string | null;
  email: string | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export function useUserAuth(): UserAuth {
  const [userId, setUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Track previous userId to detect login/logout
  const prevUserIdRef = useRef<string | null>(null);
  
  const isAuthenticated = !!accessToken && !!userId;

  useEffect(() => {
    let active = true;
    
    (async () => {
      try {
        // Handle Supabase tokens delivered via URL hash (magic link / recovery / OAuth)
        const hash = window.location.hash || "";
        if (hash && !hash.startsWith("#/")) {
          const raw = hash.startsWith("#") ? hash.slice(1) : hash;
          const params = new URLSearchParams(raw);
          const at = params.get("access_token");
          const rt = params.get("refresh_token");
          const type = params.get("type");
          
          // Check if this is an OAuth callback (not recovery)
          const isOAuthCallback = at && rt && type && type !== "recovery";
          
          if (at && rt) {
            // Store return URL from sessionStorage before cleaning hash (for OAuth callbacks)
            if (isOAuthCallback) {
              const storedReturnUrl = sessionStorage.getItem("oauth_return_url");
              // Keep it in sessionStorage for UserAuthPage to pick up
              if (!storedReturnUrl) {
                // Try to extract from hash if not in sessionStorage
                const returnUrlFromHash = params.get("state") || "#/account";
                sessionStorage.setItem("oauth_return_url", returnUrlFromHash);
              }
            }
            
            await supabase.auth.setSession({ access_token: at, refresh_token: rt });
            const cleaned = window.location.pathname + window.location.search + "#/";
            window.history.replaceState(null, "", cleaned);
          }
        }

        const { data } = await supabase.auth.getSession();
        if (!active) return;
        
        const session = data.session;
        const initialUserId = session?.user?.id ?? null;
        const initialUserEmail = session?.user?.email ?? null;
        
        setAccessToken(session?.access_token ?? null);
        setUserEmail(initialUserEmail);
        setUserId(initialUserId);
        
        // Track analytics identity on initial load
        if (initialUserId) {
          identifyUser(initialUserId, initialUserEmail);
        }
        
        prevUserIdRef.current = initialUserId;
      } finally {
        if (active) setIsLoading(false);
      }
    })();

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      const newUserId = session?.user?.id ?? null;
      const newUserEmail = session?.user?.email ?? null;
      
      setAccessToken(session?.access_token ?? null);
      setUserEmail(newUserEmail);
      setUserId(newUserId);
      
      // Track analytics identity changes
      if (newUserId && prevUserIdRef.current !== newUserId) {
        // User logged in
        identifyUser(newUserId, newUserEmail);
      } else if (!newUserId && prevUserIdRef.current !== null) {
        // User logged out
        resetUser();
      }
      
      prevUserIdRef.current = newUserId;
    });
    
    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  return {
    userId,
    email: userEmail,
    accessToken,
    isAuthenticated,
    isLoading,
  };
}

























