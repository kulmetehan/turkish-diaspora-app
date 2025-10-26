import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState } from "react";

export function useAuth() {
    const [userEmail, setUserEmail] = useState<string | null>(null);
    const [accessToken, setAccessToken] = useState<string | null>(null);
    const isAuthenticated = !!accessToken;

    useEffect(() => {
        let active = true;
        // Handle Supabase tokens delivered via URL hash (magic link / recovery)
        // Example: #access_token=..&refresh_token=..&type=recovery
        const hash = window.location.hash || "";
        if (hash && !hash.startsWith("#/")) {
            const raw = hash.startsWith("#") ? hash.slice(1) : hash;
            const params = new URLSearchParams(raw);
            const at = params.get("access_token");
            const rt = params.get("refresh_token");
            if (at && rt) {
                void supabase.auth.setSession({ access_token: at, refresh_token: rt }).then(() => {
                    // Clean up the URL hash to a normal app route
                    const cleaned = window.location.pathname + window.location.search + "#/";
                    window.history.replaceState(null, "", cleaned);
                }).catch(() => {/* no-op */ });
            }
        }
        supabase.auth.getSession().then(({ data }) => {
            if (!active) return;
            const s = data.session;
            setAccessToken(s?.access_token ?? null);
            setUserEmail(s?.user?.email ?? null);
        });
        const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
            setAccessToken(session?.access_token ?? null);
            setUserEmail(session?.user?.email ?? null);
        });
        return () => { active = false; sub.subscription.unsubscribe(); };
    }, []);

    return { userEmail, accessToken, isAuthenticated };
}