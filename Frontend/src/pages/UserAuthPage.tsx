// Frontend/src/pages/UserAuthPage.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { supabase } from "@/lib/supabaseClient";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { getOrCreateClientId, claimReferral } from "@/lib/api";
import { AppViewportShell, PageShell } from "@/components/layout";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function UserAuthPage() {
  const [activeTab, setActiveTab] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [referralCode, setReferralCode] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();
  const location = useLocation();

  // Extract referral code from URL hash query params
  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.includes("?")) {
      const params = new URLSearchParams(hash.split("?")[1]);
      const refCode = params.get("ref");
      if (refCode) {
        setReferralCode(refCode.toUpperCase());
        setActiveTab("signup"); // Switch to signup tab if referral code present
      }
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        toast.error("Inloggen mislukt", { description: error.message });
        return;
      }

      if (data.session) {
        // Migrate client_id activity to user_id
        const clientId = getOrCreateClientId();
        try {
          // Call migration endpoint
          const response = await fetch("/api/v1/auth/migrate-client-id", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${data.session.access_token}`,
            },
            body: JSON.stringify({ client_id: clientId }),
          });

          if (response.ok) {
            toast.success("Welkom terug!", { description: "Je activiteit is gemigreerd." });
          }
        } catch (migrationError) {
          console.warn("Failed to migrate client_id:", migrationError);
          // Don't fail login if migration fails
        }

        toast.success("Ingelogd!");
        nav("/account", { replace: true });
      }
    } catch (err) {
      toast.error("Inloggen mislukt", {
        description: err instanceof Error ? err.message : "Onbekende fout",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            display_name: displayName || undefined,
          },
        },
      });

      if (error) {
        toast.error("Registreren mislukt", { description: error.message });
        return;
      }

      if (data.user) {
        // Migrate client_id activity to user_id
        const clientId = getOrCreateClientId();
        if (data.session) {
          try {
            const response = await fetch("/api/v1/auth/migrate-client-id", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${data.session.access_token}`,
              },
              body: JSON.stringify({ client_id: clientId }),
            });

            if (response.ok) {
              toast.success("Account aangemaakt!", { description: "Je activiteit is gemigreerd." });
            }
          } catch (migrationError) {
            console.warn("Failed to migrate client_id:", migrationError);
          }

          // Claim referral code if present
          if (referralCode && referralCode.trim()) {
            try {
              const claimResult = await claimReferral(referralCode.trim());
              if (claimResult.success) {
                toast.success("Referral code gebruikt!", {
                  description: claimResult.message,
                });
              }
            } catch (refError: any) {
              // Don't fail signup if referral claim fails
              console.warn("Failed to claim referral:", refError);
              if (refError.message && !refError.message.includes("already")) {
                toast.error("Referral code kon niet worden gebruikt", {
                  description: refError.message,
                });
              }
            }
          }
        }

        toast.success("Welkom bij Turkspot!", {
          description: "Je account is aangemaakt. Je kunt nu inloggen.",
        });
        
        // Switch to login tab if email confirmation is required
        if (!data.session) {
          setActiveTab("login");
        } else {
          nav("/account", { replace: true });
        }
      }
    } catch (err) {
      toast.error("Registreren mislukt", {
        description: err instanceof Error ? err.message : "Onbekende fout",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Inloggen / Registreren"
        subtitle="Maak een account aan of log in om je activiteit te behouden"
        maxWidth="md"
      >
        <Card className="w-full max-w-md mx-auto">
          <CardHeader>
            <CardTitle>Turkspot Account</CardTitle>
            <CardDescription>
              Log in of maak een account aan om je activiteit bij te houden
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "login" | "signup")}>
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login">Inloggen</TabsTrigger>
                <TabsTrigger value="signup">Registreren</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <Input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Wachtwoord</Label>
                    <Input
                      id="login-password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" disabled={loading} className="w-full">
                    {loading ? "Inloggen..." : "Inloggen"}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="signup">
                <form onSubmit={handleSignup} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="signup-email">Email</Label>
                    <Input
                      id="signup-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-password">Wachtwoord</Label>
                    <Input
                      id="signup-password"
                      type="password"
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={6}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-display-name">Weergavenaam (optioneel)</Label>
                    <Input
                      id="signup-display-name"
                      type="text"
                      autoComplete="name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Je naam"
                    />
                  </div>
                  {referralCode && (
                    <div className="space-y-2">
                      <Label htmlFor="signup-referral-code">Referral Code (optioneel)</Label>
                      <Input
                        id="signup-referral-code"
                        type="text"
                        value={referralCode}
                        onChange={(e) => setReferralCode(e.target.value.toUpperCase())}
                        placeholder="REFCODE"
                        className="font-mono"
                      />
                      <p className="text-xs text-muted-foreground">
                        Gebruik een referral code van een vriend voor een welcome bonus!
                      </p>
                    </div>
                  )}
                  <Button type="submit" disabled={loading} className="w-full">
                    {loading ? "Account aanmaken..." : "Account aanmaken"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
          <CardFooter>
            <p className="text-xs text-muted-foreground text-center w-full">
              Door je aan te melden ga je akkoord met onze{" "}
              <a href="#/terms" className="underline">
                gebruiksvoorwaarden
              </a>{" "}
              en{" "}
              <a href="#/privacy" className="underline">
                privacybeleid
              </a>
              .
            </p>
          </CardFooter>
        </Card>
      </PageShell>
    </AppViewportShell>
  );
}

