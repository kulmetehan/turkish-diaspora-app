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
        console.log("[useUserAuth] ===== useUserAuth useEffect Starting =====");
        console.log("[useUserAuth] Current URL:", window.location.href);
        
        // First, check for pending tokens stored by index.html script (before HashRouter navigated away)
        const pendingTokensStr = sessionStorage.getItem("pending_oauth_tokens");
        let pendingTokens: { access_token: string; refresh_token: string; route: string } | null = null;
        
        if (pendingTokensStr) {
          try {
            pendingTokens = JSON.parse(pendingTokensStr);
            console.log("[useUserAuth] ✓ Found pending tokens in sessionStorage!");
            console.log("[useUserAuth] Pending route:", pendingTokens.route);
            // Remove immediately to prevent reprocessing
            sessionStorage.removeItem("pending_oauth_tokens");
          } catch (e) {
            console.error("[useUserAuth] Failed to parse pending tokens:", e);
            sessionStorage.removeItem("pending_oauth_tokens");
          }
        }
        
        // Handle Supabase tokens delivered via URL hash (magic link / recovery / OAuth)
        // Can be in format: #access_token=... OR #/auth#access_token=... (double hash from OAuth redirect)
        // First, check if there are tokens in the URL hash
        const hash = window.location.hash || "";
        console.log("[useUserAuth] Initial hash:", hash);
        console.log("[useUserAuth] Hash length:", hash.length);
        
        // Get return URL from sessionStorage (set by GoogleLoginButton before OAuth redirect)
        // This is the page the user came from (e.g., #/feed, #/account)
        // Priority: oauth_return_url from GoogleLoginButton > route from pending tokens > default to #/feed
        let routePart = sessionStorage.getItem("oauth_return_url") || "";
        console.log("[useUserAuth] Stored oauth_return_url from sessionStorage:", routePart);
        
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
          console.log("[useUserAuth] Using pending tokens from sessionStorage");
          console.log("[useUserAuth] Route part from pending tokens:", pendingTokens.route);
          console.log("[useUserAuth] Final route part (oauth_return_url takes priority):", routePart);
          console.log("[useUserAuth] Access token exists:", !!accessToken);
          console.log("[useUserAuth] Refresh token exists:", !!refreshToken);
        }
        
        // Only parse from hash if we don't have pending tokens
        if (!pendingTokens && hash && (hash.includes("access_token") || hash.includes("refresh_token"))) {
          hasTokensInHash = true;
          console.log("[useUserAuth] ✓ Tokens found in hash!");
          
          // Extract route part if double hash format
          if (hash.includes("#access_token")) {
            const tokenStart = hash.indexOf("#access_token");
            console.log("[useUserAuth] Token start position:", tokenStart);
            console.log("[useUserAuth] Hash before tokenStart:", hash.substring(0, tokenStart));
            console.log("[useUserAuth] Character before tokenStart:", hash[tokenStart - 1]);
            
            // Check if there's a route part before the tokens (double hash format: #/auth#access_token=...)
            if (tokenStart > 1) {
              const potentialRoutePart = hash.substring(0, tokenStart);
              
              // Check if this looks like a route (starts with #/)
              if (potentialRoutePart.startsWith("#/")) {
                // Double hash detected: #/auth#access_token=...
                console.log("[useUserAuth] ✓ Double hash detected!");
                routePart = potentialRoutePart;
                const tokenPart = hash.substring(tokenStart); // Keep the # for #access_token
                
                console.log("[useUserAuth] Route part:", routePart);
                console.log("[useUserAuth] Token part (first 100 chars):", tokenPart.substring(0, 100) + "...");
                
                // Store return URL
                if (!sessionStorage.getItem("oauth_return_url")) {
                  sessionStorage.setItem("oauth_return_url", routePart);
                  console.log("[useUserAuth] ✓ Stored oauth_return_url:", routePart);
                }
                
                // Parse tokens from hash (tokenPart already starts with #)
                const raw = tokenPart.startsWith("#") ? tokenPart.slice(1) : tokenPart;
                const params = new URLSearchParams(raw);
                accessToken = params.get("access_token");
                refreshToken = params.get("refresh_token");
                
                console.log("[useUserAuth] Extracted accessToken:", accessToken ? accessToken.substring(0, 20) + "..." : "null");
                console.log("[useUserAuth] Extracted refreshToken:", refreshToken ? refreshToken.substring(0, 20) + "..." : "null");
              } else {
                // Single hash format: #access_token=... (or something else before it)
                console.log("[useUserAuth] Single hash format detected (route part doesn't start with #/)");
                const raw = hash.startsWith("#") ? hash.slice(1) : hash;
                const params = new URLSearchParams(raw);
                accessToken = params.get("access_token");
                refreshToken = params.get("refresh_token");
                
                console.log("[useUserAuth] Extracted accessToken:", accessToken ? accessToken.substring(0, 20) + "..." : "null");
                console.log("[useUserAuth] Extracted refreshToken:", refreshToken ? refreshToken.substring(0, 20) + "..." : "null");
              }
            } else {
              // Single hash format: #access_token=... (tokens at start)
              console.log("[useUserAuth] Single hash format detected (tokens at start)");
              const raw = hash.startsWith("#") ? hash.slice(1) : hash;
              const params = new URLSearchParams(raw);
              accessToken = params.get("access_token");
              refreshToken = params.get("refresh_token");
              
              console.log("[useUserAuth] Extracted accessToken:", accessToken ? accessToken.substring(0, 20) + "..." : "null");
              console.log("[useUserAuth] Extracted refreshToken:", refreshToken ? refreshToken.substring(0, 20) + "..." : "null");
            }
          }
        } else if (!pendingTokens) {
          console.log("[useUserAuth] No tokens found in hash");
        }
        
        // If we have tokens (from pending tokens OR hash), set the session
        if (accessToken && refreshToken) {
          console.log("[useUserAuth] ✓ Tokens available, calling setSession...");
          console.log("[useUserAuth] Access token (first 20 chars):", accessToken.substring(0, 20) + "...");
          console.log("[useUserAuth] Refresh token (first 20 chars):", refreshToken.substring(0, 20) + "...");
          
          // Manually set the session with tokens
          const { data: sessionData, error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          
          if (sessionError) {
            console.error("[useUserAuth] ✗ Failed to set session:", sessionError);
            console.error("[useUserAuth] Error details:", JSON.stringify(sessionError, null, 2));
          } else {
            console.log("[useUserAuth] ✓ setSession completed");
            console.log("[useUserAuth] Session data exists:", !!sessionData.session);
            console.log("[useUserAuth] User ID:", sessionData.session?.user?.id);
            console.log("[useUserAuth] User email:", sessionData.session?.user?.email);
          }
        } else if (hasTokensInHash) {
          console.warn("[useUserAuth] ⚠ Tokens expected but extraction failed");
          console.warn("[useUserAuth] accessToken:", accessToken);
          console.warn("[useUserAuth] refreshToken:", refreshToken);
        }
        
        // Always check for existing session (may have been set by Supabase's detectSessionInUrl)
        console.log("[useUserAuth] Checking for existing session...");
        const { data, error: sessionCheckError } = await supabase.auth.getSession();
        
        if (sessionCheckError) {
          console.error("[useUserAuth] ✗ Error checking session:", sessionCheckError);
        } else {
          console.log("[useUserAuth] Session check result:");
          console.log("[useUserAuth] - Session exists:", !!data.session);
          console.log("[useUserAuth] - User ID:", data.session?.user?.id);
          console.log("[useUserAuth] - User email:", data.session?.user?.email);
          console.log("[useUserAuth] - Access token exists:", !!data.session?.access_token);
        }
        
        // If we had tokens in hash and now have a session, clean up the hash
        if (hasTokensInHash && data.session) {
          console.log("[useUserAuth] ✓ Session detected with tokens in hash, cleaning up hash");
          
          // ALWAYS read oauth_return_url fresh from sessionStorage (don't use routePart variable)
          // This ensures we get the correct return URL even if it was set after component mount
          const storedReturnUrl = sessionStorage.getItem("oauth_return_url");
          const targetRoute = storedReturnUrl || "#/feed";
          console.log("[useUserAuth] Stored oauth_return_url from sessionStorage:", storedReturnUrl);
          console.log("[useUserAuth] Target route:", targetRoute);
          
          // Clear oauth_return_url BEFORE redirect to prevent loops
          sessionStorage.removeItem("oauth_return_url");
          console.log("[useUserAuth] ✓ Cleared oauth_return_url from sessionStorage");
          
          // Clean up the hash using window.location.hash for HashRouter compatibility
          console.log("[useUserAuth] Setting hash to:", targetRoute);
          window.location.hash = targetRoute;
          console.log("[useUserAuth] ✓ Hash set to:", window.location.hash);
        } else if (hasTokensInHash && !data.session) {
          console.warn("[useUserAuth] ⚠ Tokens in hash but no session found!");
        }
        
        if (!active) {
          console.log("[useUserAuth] Component unmounted, returning early");
          return;
        }
        
        const session = data.session;
        const initialUserId = session?.user?.id ?? null;
        const initialUserEmail = session?.user?.email ?? null;
        
        console.log("[useUserAuth] Setting state:");
        console.log("[useUserAuth] - userId:", initialUserId);
        console.log("[useUserAuth] - email:", initialUserEmail);
        console.log("[useUserAuth] - accessToken exists:", !!session?.access_token);
        
        setAccessToken(session?.access_token ?? null);
        setUserEmail(initialUserEmail);
        setUserId(initialUserId);
        
        if (initialUserId) {
          console.log("[useUserAuth] ✓ Calling identifyUser for analytics");
          identifyUser(initialUserId, initialUserEmail);
        }
        
        prevUserIdRef.current = initialUserId;
        console.log("[useUserAuth] ===== useEffect Complete =====");
      } finally {
        if (active) setIsLoading(false);
      }
    })();

    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      console.log("[useUserAuth] ===== onAuthStateChange Event =====");
      console.log("[useUserAuth] Event type:", event);
      console.log("[useUserAuth] Session exists:", !!session);
      console.log("[useUserAuth] User ID:", session?.user?.id);
      console.log("[useUserAuth] User email:", session?.user?.email);
      console.log("[useUserAuth] Access token exists:", !!session?.access_token);
      console.log("[useUserAuth] Current hash:", window.location.hash);
      
      const newUserId = session?.user?.id ?? null;
      const newUserEmail = session?.user?.email ?? null;
      
      setAccessToken(session?.access_token ?? null);
      setUserEmail(newUserEmail);
      setUserId(newUserId);
      
      // Clean up hash if we have a session and tokens are still in the URL
      if (session && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED")) {
        const hash = window.location.hash || "";
        console.log("[useUserAuth] Checking hash for cleanup. Hash:", hash);
        
        if (hash && (hash.includes("access_token") || hash.includes("refresh_token"))) {
          console.log("[useUserAuth] ✓ Tokens still in hash, cleaning up...");
          
          // ALWAYS read oauth_return_url fresh from sessionStorage (don't use closure variable)
          // This ensures we get the correct return URL even if it was set after component mount
          const storedReturnUrl = sessionStorage.getItem("oauth_return_url");
          const targetRoute = storedReturnUrl || "#/feed";
          console.log("[useUserAuth] Stored oauth_return_url from sessionStorage:", storedReturnUrl);
          console.log("[useUserAuth] Target route:", targetRoute);
          
          // Clear oauth_return_url BEFORE redirect to prevent loops
          sessionStorage.removeItem("oauth_return_url");
          console.log("[useUserAuth] ✓ Cleared oauth_return_url from sessionStorage");
          
          // Clean up the hash using window.location.hash for HashRouter compatibility
          console.log("[useUserAuth] Setting hash to:", targetRoute);
          window.location.hash = targetRoute;
          console.log("[useUserAuth] ✓ Hash set to:", window.location.hash);
        } else {
          console.log("[useUserAuth] No tokens in hash, no cleanup needed");
        }
      }
      
      // Track analytics identity changes
      if (newUserId && prevUserIdRef.current !== newUserId) {
        // User logged in
        console.log("[useUserAuth] ✓ User logged in, calling identifyUser");
        identifyUser(newUserId, newUserEmail);
      } else if (!newUserId && prevUserIdRef.current !== null) {
        // User logged out
        console.log("[useUserAuth] ✓ User logged out, calling resetUser");
        resetUser();
      }
      
      prevUserIdRef.current = newUserId;
      console.log("[useUserAuth] ===== onAuthStateChange Complete =====");
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

























