import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { supabase } from "@/lib/supabaseClient";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const nav = useNavigate();
    const loc = useLocation() as any;

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault(); setError(null); setLoading(true);
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        setLoading(false);
        if (error) { setError(error.message); return; }
        const dest = loc.state?.from?.pathname || "/admin";
        nav(dest, { replace: true });
    };

    return (
        <div className="flex items-center justify-center py-12">
            <Card className="w-full max-w-sm">
                <CardHeader>
                    <CardTitle>Admin Login (Restricted Area)</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={onSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input id="email" name="email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required />
                        </div>
                        {error && <div className="text-red-600 text-sm">{error}</div>}
                        <Button type="submit" disabled={loading} className="w-full">{loading ? "Signing in…" : "Sign in"}</Button>
                    </form>
                </CardContent>
                <CardFooter>
                    <p className="text-xs text-muted-foreground">No public signup. Admins only.</p>
                </CardFooter>
            </Card>
        </div>
    );
}


