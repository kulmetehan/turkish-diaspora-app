// Frontend/src/hooks/useUserAuth.ts
import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState } from "react";

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
  
  const isAuthenticated = !!accessToken && !!userId;

  useEffect(() => {
    let active = true;
    
    (async () => {
      try {
        // Handle Supabase tokens delivered via URL hash (magic link / recovery)
        const hash = window.location.hash || "";
        if (hash && !hash.startsWith("#/")) {
          const raw = hash.startsWith("#") ? hash.slice(1) : hash;
          const params = new URLSearchParams(raw);
          const at = params.get("access_token");
          const rt = params.get("refresh_token");
          if (at && rt) {
            await supabase.auth.setSession({ access_token: at, refresh_token: rt });
            const cleaned = window.location.pathname + window.location.search + "#/";
            window.history.replaceState(null, "", cleaned);
          }
        }

        const { data } = await supabase.auth.getSession();
        if (!active) return;
        
        const session = data.session;
        setAccessToken(session?.access_token ?? null);
        setUserEmail(session?.user?.email ?? null);
        setUserId(session?.user?.id ?? null);
      } finally {
        if (active) setIsLoading(false);
      }
    })();

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setAccessToken(session?.access_token ?? null);
      setUserEmail(session?.user?.email ?? null);
      setUserId(session?.user?.id ?? null);
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



