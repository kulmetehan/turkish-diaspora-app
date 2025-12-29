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
        // Can be in format: #access_token=... OR #/auth#access_token=... (double hash from OAuth redirect)
        // First, check if there are tokens in the URL hash
        const hash = window.location.hash || "";
        let routePart = sessionStorage.getItem("oauth_return_url") || "";
        let hasTokensInHash = false;
        let accessToken: string | null = null;
        let refreshToken: string | null = null;
        
        if (hash && (hash.includes("access_token") || hash.includes("refresh_token"))) {
          hasTokensInHash = true;
          
          // Extract route part if double hash format
          if (hash.includes("#access_token")) {
            const tokenStart = hash.indexOf("#access_token");
            if (tokenStart > 0 && hash[tokenStart - 1] === "#") {
              // Double hash detected: #/auth#access_token=...
              routePart = hash.substring(0, tokenStart);
              const tokenPart = hash.substring(tokenStart + 1);
              
              // Store return URL
              if (routePart.startsWith("#/") && !sessionStorage.getItem("oauth_return_url")) {
                sessionStorage.setItem("oauth_return_url", routePart);
              }
              
              // Parse tokens from normalized hash
              const raw = tokenPart.startsWith("#") ? tokenPart.slice(1) : tokenPart;
              const params = new URLSearchParams(raw);
              accessToken = params.get("access_token");
              refreshToken = params.get("refresh_token");
            } else {
              // Single hash format: #access_token=...
              const raw = hash.startsWith("#") ? hash.slice(1) : hash;
              const params = new URLSearchParams(raw);
              accessToken = params.get("access_token");
              refreshToken = params.get("refresh_token");
            }
          }
          
          // If we have tokens, set the session
          if (accessToken && refreshToken) {
            console.log("[useUserAuth] Found tokens in URL hash, setting session...");
            
            // Manually set the session with tokens from URL
            const { data: sessionData, error: sessionError } = await supabase.auth.setSession({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
            
            if (sessionError) {
              console.error("[useUserAuth] Failed to set session:", sessionError);
            } else {
              console.log("[useUserAuth] setSession completed, sessionData:", !!sessionData.session);
            }
          }
        }
        
        // Always check for existing session (may have been set by Supabase's detectSessionInUrl)
        const { data } = await supabase.auth.getSession();
        
        // If we had tokens in hash and now have a session, clean up the hash
        if (hasTokensInHash && data.session) {
          console.log("[useUserAuth] Session detected, cleaning up hash. Route part:", routePart);
          
          // Clean up the hash using window.location.hash for HashRouter compatibility
          const targetRoute = routePart || "#/";
          window.location.hash = targetRoute;
          
          // Also clear the oauth_return_url from sessionStorage
          sessionStorage.removeItem("oauth_return_url");
        }
        
        if (!active) return;
        
        const session = data.session;
        const initialUserId = session?.user?.id ?? null;
        const initialUserEmail = session?.user?.email ?? null;
        
        setAccessToken(session?.access_token ?? null);
        setUserEmail(initialUserEmail);
        setUserId(initialUserId);
        
        if (initialUserId) {
          identifyUser(initialUserId, initialUserEmail);
        }
        
        prevUserIdRef.current = initialUserId;
      } finally {
        if (active) setIsLoading(false);
      }
    })();

    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      const newUserId = session?.user?.id ?? null;
      const newUserEmail = session?.user?.email ?? null;
      
      setAccessToken(session?.access_token ?? null);
      setUserEmail(newUserEmail);
      setUserId(newUserId);
      
      // Clean up hash if we have a session and tokens are still in the URL
      if (session && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) {
        const hash = window.location.hash || "";
        if (hash && (hash.includes("access_token") || hash.includes("refresh_token"))) {
          console.log("[useUserAuth] onAuthStateChange: Session detected, cleaning up hash");
          
          // Get stored return URL or default
          const routePart = sessionStorage.getItem("oauth_return_url") || "#/";
          sessionStorage.removeItem("oauth_return_url");
          
          // Clean up the hash using window.location.hash for HashRouter compatibility
          window.location.hash = routePart;
        }
      }
      
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

























