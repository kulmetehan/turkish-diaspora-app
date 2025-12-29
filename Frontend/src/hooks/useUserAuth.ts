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
          // Normalize double hash format: #/auth#access_token=... -> #access_token=...
          // This allows Supabase's detectSessionInUrl to work properly
          let normalizedHash = hash;
          let routePart = "";
          
          if (hash.includes("#access_token") || hash.includes("#refresh_token")) {
            const tokenStart = hash.indexOf("#access_token");
            if (tokenStart > 0 && hash[tokenStart - 1] === "#") {
              // Double hash detected: #/auth#access_token=...
              routePart = hash.substring(0, tokenStart);
              const tokenPart = hash.substring(tokenStart + 1);
              normalizedHash = tokenPart;
              
              // Store return URL
              if (!sessionStorage.getItem("oauth_return_url") && routePart.startsWith("#/")) {
                sessionStorage.setItem("oauth_return_url", routePart);
              }
              
              // Temporarily normalize the hash so Supabase can detect it
              // We'll restore it after Supabase processes it
              window.location.hash = normalizedHash;
              
              // Wait for Supabase to process (detectSessionInUrl runs automatically)
              await new Promise(resolve => setTimeout(resolve, 50));
            }
          }
          
          // Now check if Supabase detected and set the session
          const { data } = await supabase.auth.getSession();
          
          // If session was set from URL, clean up the hash
          if (data.session && (hash.includes("access_token") || hash.includes("refresh_token"))) {
            const cleaned = window.location.pathname + window.location.search + (routePart || "#/");
            window.history.replaceState(null, "", cleaned);
          }
          
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
        } else {
          // No hash, just get existing session
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
        }
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

























