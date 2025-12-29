import { useState } from "react";
import { useNavigate } from "react-router-dom";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { supabase } from "@/lib/supabaseClient";
import { toast } from "sonner";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { getRecaptchaToken } from "@/lib/recaptcha";
import { GoogleLoginButton } from "@/components/auth/GoogleLoginButton";

interface LoginModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function LoginModal({ open, onOpenChange }: LoginModalProps) {
  const [activeTab, setActiveTab] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [showEmailPassword, setShowEmailPassword] = useState(false);
  const nav = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        toast.error("Inloggen mislukt", {
          description: error.message,
        });
        return;
      }

      toast.success("Ingelogd!");
      onOpenChange(false);
      // Reset form
      setEmail("");
      setPassword("");
    } catch (error) {
      toast.error("Inloggen mislukt", {
        description: error instanceof Error ? error.message : "Onbekende fout",
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

          if (!verifyResponse.ok) {
            console.warn("reCAPTCHA verification failed, continuing with signup");
          }
        } catch (verifyError) {
          console.warn("reCAPTCHA verification error (non-critical):", verifyError);
          // Continue with signup even if verification fails
        }
      }

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            display_name: displayName || null,
          },
        },
      });

      if (error) {
        toast.error("Registreren mislukt", {
          description: error.message,
        });
        return;
      }

      toast.success("Account aangemaakt! Check je email voor verificatie.");
      onOpenChange(false);
      // Reset form
      setEmail("");
      setPassword("");
      setDisplayName("");
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'LoginModal.tsx:180',message:'signup catch error',data:{error:String(error),errorType:error instanceof Error ? error.constructor.name : typeof error},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
      // #endregion
      
      toast.error("Registreren mislukt", {
        description: error instanceof Error ? error.message : "Onbekende fout",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className={cn(
            "fixed inset-0 z-[55] bg-black/40 backdrop-blur",
            "pointer-events-none data-[state=open]:pointer-events-auto",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
          )}
        />
        <DialogPrimitive.Content
          className={cn(
            "fixed inset-x-0 bottom-0 top-auto z-[60] mx-auto w-full max-w-screen-sm",
            "flex max-h-[min(90vh,600px)] flex-col rounded-t-[40px] border border-white/15 bg-surface-raised/95 text-foreground shadow-[0_-40px_80px_rgba(0,0,0,0.6)] backdrop-blur-2xl",
            "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
            "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
            "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,500px)] lg:max-w-[min(90vw,500px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
            "lg:rounded-[40px] lg:px-6 lg:pb-6 lg:shadow-[0_45px_90px_rgba(0,0,0,0.6)]",
            "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95",
          )}
          aria-labelledby="login-modal-title"
        >
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
            <DialogPrimitive.Title
              id="login-modal-title"
              className="text-2xl font-semibold tracking-tight"
            >
              Inloggen / Registreren
            </DialogPrimitive.Title>
            <DialogPrimitive.Close className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-primary/30">
              <X className="h-5 w-5" aria-label="Sluiten" />
            </DialogPrimitive.Close>
          </div>

          <div className="flex-1 overflow-y-auto -mx-5 px-5">
            <Card className="w-full border-0 shadow-none bg-transparent">
              <CardHeader className="px-0">
                <CardTitle>Turkspot Account</CardTitle>
                <CardDescription>
                  Log in of maak een account aan om je activiteit bij te houden
                </CardDescription>
              </CardHeader>
              <CardContent className="px-0">
                {/* Google Login Button - PRIMARY */}
                <div className="mb-6">
                  <GoogleLoginButton
                    fullWidth
                    size="lg"
                    variant="default"
                    onSuccess={() => {
                      // Close modal on success
                      onOpenChange(false);
                    }}
                  />
                </div>

                {/* Conditional: Show ghost button to reveal email/password */}
                {!showEmailPassword && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowEmailPassword(true)}
                    className="w-full text-muted-foreground"
                  >
                    Of gebruik email / wachtwoord
                  </Button>
                )}

                {/* Conditional: Show divider and email/password forms */}
                {showEmailPassword && (
                  <>
                    {/* Divider */}
                    <div className="relative my-6">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-surface-raised/95 px-2 text-muted-foreground">
                          Of gebruik email / wachtwoord
                        </span>
                      </div>
                    </div>

                    {/* Email/Password Forms - SECONDARY */}
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
                  </>
                )}
              </CardContent>
              <CardFooter className="px-0">
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
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

