import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState } from "react";

export function useAuth() {
    const [userEmail, setUserEmail] = useState<string | null>(null);
    const [accessToken, setAccessToken] = useState<string | null>(null);
    const isAuthenticated = !!accessToken;

    useEffect(() => {
        let active = true;
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


