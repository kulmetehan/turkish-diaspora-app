// Frontend/src/hooks/useUserAuth.ts
import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState, useRef } from "react";
import { identifyUser, resetUser } from "@/lib/analytics";
import { setLastKnownUserId } from "@/lib/api";

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
        // First, check for pending tokens stored by index.html script (before HashRouter navigated away)
        const pendingTokensStr = sessionStorage.getItem("pending_oauth_tokens");
        let pendingTokens: { access_token: string; refresh_token: string; route: string } | null = null;
        
        if (pendingTokensStr) {
          try {
            pendingTokens = JSON.parse(pendingTokensStr);
            // Remove immediately to prevent reprocessing
            sessionStorage.removeItem("pending_oauth_tokens");
          } catch (e) {
            console.error("[useUserAuth] Failed to parse pending tokens:", e);
            sessionStorage.removeItem("pending_oauth_tokens");
          }
        }
        
        // Handle Supabase tokens delivered via URL hash (magic link / recovery / OAuth)
        // Can be in format: #access_token=... OR #/auth#access_token=... (double hash from OAuth redirect)
        const hash = window.location.hash || "";
        
        // Get return URL from sessionStorage (set by GoogleLoginButton before OAuth redirect)
        // This is the page the user came from (e.g., #/feed, #/account)
        // Priority: oauth_return_url from GoogleLoginButton > route from pending tokens > default to #/feed
        let routePart = sessionStorage.getItem("oauth_return_url") || "";
        
        let hasTokensInHash = false;
        let accessToken: string | null = null;
        let refreshToken: string | null = null;
        
        // Use pending tokens if available (from index.html script), otherwise parse from hash
        if (pendingTokens) {
          accessToken = pendingTokens.access_token;
          refreshToken = pendingTokens.refresh_token;
          // Only use route from pending tokens if oauth_return_url is not already set
          // The oauth_return_url from GoogleLoginButton is the correct return destination
          if (!routePart) {
            routePart = pendingTokens.route || "";
          }
          hasTokensInHash = true;
        }
        
        // Only parse from hash if we don't have pending tokens
        if (!pendingTokens && hash && (hash.includes("access_token") || hash.includes("refresh_token"))) {
          hasTokensInHash = true;
          
          // Extract route part if double hash format
          if (hash.includes("#access_token")) {
            const tokenStart = hash.indexOf("#access_token");
            
            // Check if there's a route part before the tokens (double hash format: #/auth#access_token=...)
            if (tokenStart > 1) {
              const potentialRoutePart = hash.substring(0, tokenStart);
              
              // Check if this looks like a route (starts with #/)
              if (potentialRoutePart.startsWith("#/")) {
                // Double hash detected: #/auth#access_token=...
                routePart = potentialRoutePart;
                const tokenPart = hash.substring(tokenStart); // Keep the # for #access_token
                
                // Store return URL
                if (!sessionStorage.getItem("oauth_return_url")) {
                  sessionStorage.setItem("oauth_return_url", routePart);
                }
                
                // Parse tokens from hash (tokenPart already starts with #)
                const raw = tokenPart.startsWith("#") ? tokenPart.slice(1) : tokenPart;
                const params = new URLSearchParams(raw);
                accessToken = params.get("access_token");
                refreshToken = params.get("refresh_token");
              } else {
                // Single hash format: #access_token=... (or something else before it)
                const raw = hash.startsWith("#") ? hash.slice(1) : hash;
                const params = new URLSearchParams(raw);
                accessToken = params.get("access_token");
                refreshToken = params.get("refresh_token");
              }
            } else {
              // Single hash format: #access_token=... (tokens at start)
              const raw = hash.startsWith("#") ? hash.slice(1) : hash;
              const params = new URLSearchParams(raw);
              accessToken = params.get("access_token");
              refreshToken = params.get("refresh_token");
            }
          }
        }
        
        // If we have tokens (from pending tokens OR hash), set the session
        if (accessToken && refreshToken) {
          // Manually set the session with tokens
          const { error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          
          if (sessionError) {
            console.error("[useUserAuth] Failed to set session:", sessionError);
          }
        } else if (hasTokensInHash) {
          console.warn("[useUserAuth] Tokens expected but extraction failed");
        }
        
        // Always check for existing session (may have been set by Supabase's detectSessionInUrl)
        const { data, error: sessionCheckError } = await supabase.auth.getSession();
        
        if (sessionCheckError) {
          console.error("[useUserAuth] Error checking session:", sessionCheckError);
        }
        
        // If we had tokens in hash and now have a session, clean up the hash
        if (hasTokensInHash && data.session) {
          // ALWAYS read oauth_return_url fresh from sessionStorage (don't use routePart variable)
          // This ensures we get the correct return URL even if it was set after component mount
          const storedReturnUrl = sessionStorage.getItem("oauth_return_url");
          const targetRoute = storedReturnUrl || "#/feed";
          
          // Clear oauth_return_url BEFORE redirect to prevent loops
          sessionStorage.removeItem("oauth_return_url");
          
          // Clean up the hash using window.location.hash for HashRouter compatibility
          window.location.hash = targetRoute;
        } else if (hasTokensInHash && !data.session) {
          console.warn("[useUserAuth] Tokens in hash but no session found!");
        }
        
        if (!active) {
          return;
        }
        
        const session = data.session;
        const initialUserId = session?.user?.id ?? null;
        const initialUserEmail = session?.user?.email ?? null;
        
        setAccessToken(session?.access_token ?? null);
        setUserEmail(initialUserEmail);
        setUserId(initialUserId);
        
        if (initialUserId) {
          identifyUser(initialUserId, initialUserEmail);
          setLastKnownUserId(initialUserId);
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
      
      // Store last known user_id for poll response tracking
      if (newUserId) {
        setLastKnownUserId(newUserId);
      }
      
      // Clean up hash if we have a session and tokens are still in the URL
      if (session && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) {
        const hash = window.location.hash || "";
        
        if (hash && (hash.includes("access_token") || hash.includes("refresh_token"))) {
          // ALWAYS read oauth_return_url fresh from sessionStorage (don't use closure variable)
          // This ensures we get the correct return URL even if it was set after component mount
          const storedReturnUrl = sessionStorage.getItem("oauth_return_url");
          const targetRoute = storedReturnUrl || "#/feed";
          
          // Clear oauth_return_url BEFORE redirect to prevent loops
          sessionStorage.removeItem("oauth_return_url");
          
          // Clean up the hash using window.location.hash for HashRouter compatibility
          window.location.hash = targetRoute;
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

























