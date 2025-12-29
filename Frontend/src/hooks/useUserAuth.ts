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
        const hash = window.location.hash || "";
        
        if (hash) {
          // Hash may have been normalized by the script in index.html
          // Check if we have tokens in the hash (either normalized or double hash format)
          let hashToParse = hash;
          let routePart = sessionStorage.getItem("oauth_return_url") || "";
          
          // Check if this is still a double hash (script may not have run yet, or hash changed)
          if (hash.includes("#access_token") || hash.includes("#refresh_token")) {
            const tokenStart = hash.indexOf("#access_token");
            if (tokenStart > 0 && hash[tokenStart - 1] === "#") {
              // Double hash detected: #/auth#access_token=...
              routePart = hash.substring(0, tokenStart);
              const tokenPart = hash.substring(tokenStart + 1);
              hashToParse = tokenPart;
              
              // Store return URL
              if (!sessionStorage.getItem("oauth_return_url") && routePart.startsWith("#/")) {
                sessionStorage.setItem("oauth_return_url", routePart);
              }
              
              // Normalize hash if script didn't do it yet
              window.location.hash = hashToParse;
              // Wait a bit for Supabase's detectSessionInUrl to process
              await new Promise(resolve => setTimeout(resolve, 100));
            }
          }
          
          // Parse tokens from hash (should be normalized by now)
          if (hashToParse && !hashToParse.startsWith("#/")) {
            const raw = hashToParse.startsWith("#") ? hashToParse.slice(1) : hashToParse;
            const params = new URLSearchParams(raw);
            const accessToken = params.get("access_token");
            const refreshToken = params.get("refresh_token");
            
            if (accessToken && refreshToken) {
              console.log("[useUserAuth] Found tokens in URL hash, setting session...");
              
              // Manually set the session with tokens from URL
              // Supabase's detectSessionInUrl may have already set it, but we ensure it's set
              const { data: sessionData, error: sessionError } = await supabase.auth.setSession({
                access_token: accessToken,
                refresh_token: refreshToken,
              });
              
              if (sessionError) {
                console.error("[useUserAuth] Failed to set session:", sessionError);
              }
              
              // Verify session was set (either manually or by Supabase's detectSessionInUrl)
              const { data: verifyData } = await supabase.auth.getSession();
              
              if (verifyData.session) {
                console.log("[useUserAuth] Session set successfully, cleaning up hash");
                
                // Session set successfully, clean up the hash
                const cleaned = window.location.pathname + window.location.search + (routePart || "#/");
                window.history.replaceState(null, "", cleaned);
                
                if (!active) return;
                
                const session = verifyData.session;
                const initialUserId = session.user?.id ?? null;
                const initialUserEmail = session.user?.email ?? null;
                
                setAccessToken(session.access_token ?? null);
                setUserEmail(initialUserEmail);
                setUserId(initialUserId);
                
                // Track analytics identity on initial load
                if (initialUserId) {
                  identifyUser(initialUserId, initialUserEmail);
                }
                
                prevUserIdRef.current = initialUserId;
                
                // Early return since we've handled the session
                if (active) setIsLoading(false);
                return;
              } else {
                console.warn("[useUserAuth] Session not set after setSession call, hash:", hash);
              }
            }
          }
        }
        
        // No tokens in URL or session already set, just get existing session
        const { data } = await supabase.auth.getSession();
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

























