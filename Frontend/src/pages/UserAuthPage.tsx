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
import { getOrCreateClientId, API_BASE } from "@/lib/api";
import { AppViewportShell, PageShell } from "@/components/layout";
import { useLocation } from "react-router-dom";
import { getRecaptchaToken } from "@/lib/recaptcha";

export default function UserAuthPage() {
  const [activeTab, setActiveTab] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();
  const location = useLocation();

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
          const response = await fetch(`${API_BASE}/api/v1/auth/migrate-client-id`, {
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
      // Get reCAPTCHA token (non-blocking, graceful degradation)
      let recaptchaToken: string | null = null;
      try {
        recaptchaToken = await getRecaptchaToken("SIGNUP");
      } catch (recaptchaError) {
        console.warn("reCAPTCHA token generation failed (non-critical):", recaptchaError);
        // Continue with signup even if reCAPTCHA fails
      }

      // Verify reCAPTCHA token on backend (non-blocking)
      if (recaptchaToken) {
        try {
          const verifyResponse = await fetch(`${API_BASE}/api/v1/auth/verify-recaptcha`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              token: recaptchaToken,
              action: "SIGNUP",
            }),
          });

          if (verifyResponse.ok) {
            const verifyResult = await verifyResponse.json();
            console.debug("reCAPTCHA verification successful:", verifyResult);
            
            // If score is low, show warning but don't block signup
            if (verifyResult.score < verifyResult.threshold) {
              console.warn(
                `reCAPTCHA score ${verifyResult.score} below threshold ${verifyResult.threshold}`
              );
            }
          } else {
            const errorData = await verifyResponse.json().catch(() => ({}));
            console.warn("reCAPTCHA verification failed:", errorData);
            // Don't block signup, just log the warning
          }
        } catch (verifyError) {
          console.warn("reCAPTCHA verification error (non-critical):", verifyError);
          // Don't block signup if verification fails
        }
      } else {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserAuthPage.tsx:152',message:'verify skipped no token',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
      }

      // Proceed with Supabase signup
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
            const response = await fetch(`${API_BASE}/api/v1/auth/migrate-client-id`, {
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

          // Send welcome email (non-blocking)
          try {
            // Detect language from browser
            const browserLang = navigator.language.toLowerCase();
            let emailLang = "nl"; // default
            if (browserLang.startsWith("tr")) {
              emailLang = "tr";
            } else if (browserLang.startsWith("en")) {
              emailLang = "en";
            }

            const welcomeResponse = await fetch(
              `${API_BASE}/api/v1/auth/send-welcome-email?language=${emailLang}`,
              {
                method: "POST",
                headers: {
                  "Authorization": `Bearer ${data.session.access_token}`,
                },
              }
            );

            if (welcomeResponse.ok) {
              // Email sent successfully (silent success)
              console.log("Welcome email sent");
            } else {
              // Don't show error to user - email failure shouldn't block signup
              console.warn("Failed to send welcome email:", await welcomeResponse.text());
            }
          } catch (emailError) {
            // Don't fail signup if email fails
            console.warn("Failed to send welcome email:", emailError);
          }

        }

        toast.success("Welkom bij Turkspot!", {
          description: "Je account is aangemaakt. Je kunt nu inloggen.",
        });
        
        // Switch to login tab if email confirmation is required
        if (!data.session) {
          setActiveTab("login");
        } else {
          // Check if user has username/profile setup
          // If not, redirect to feed which will show onboarding
          try {
            const { getCurrentUser } = await import("@/lib/api");
            const profile = await getCurrentUser();
            if (!profile?.name) {
              // User doesn't have username, redirect to feed (will show onboarding)
              nav("/feed", { replace: true });
            } else {
              // User has profile, go to account page
              nav("/account", { replace: true });
            }
          } catch (error) {
            console.error("Failed to check profile:", error);
            // Fallback to account page
            nav("/account", { replace: true });
          }
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

