import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { trackClaimFlowCompleted } from "@/lib/analytics";

type Props = {
    onSubmit: (data: { google_business_link?: string }) => Promise<void>;
    isSubmitting: boolean;
    locationId?: number;
    claimToken?: string;
};

export function ClaimForm({ onSubmit, isSubmitting, locationId, claimToken }: Props) {
    const [googleBusinessLink, setGoogleBusinessLink] = useState("");
    const [error, setError] = useState<string | null>(null);
    const flowStartTimeRef = useRef<number | null>(null);

    // Track flow start time when form is mounted (for dialog flow)
    useEffect(() => {
        if (locationId && claimToken) {
            flowStartTimeRef.current = Date.now();
        }
    }, [locationId, claimToken]);

    const validateUrl = (url: string): boolean => {
        if (!url.trim()) return true; // Empty is OK (optional field)
        try {
            const parsed = new URL(url);
            return parsed.protocol === "http:" || parsed.protocol === "https:";
        } catch {
            return false;
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate: at least one field must be filled
        if (!googleBusinessLink.trim()) {
            setError("Vul minimaal één veld in (Google Business link)");
            return;
        }

        // Validate URL format if provided
        if (googleBusinessLink.trim() && !validateUrl(googleBusinessLink.trim())) {
            setError("Google Business link moet een geldige URL zijn (begint met http:// of https://)");
            return;
        }

        try {
            await onSubmit({
                google_business_link: googleBusinessLink.trim() || undefined,
            });
            
            // Track claim flow completed (for dialog flow)
            if (locationId && claimToken && flowStartTimeRef.current) {
                const flowDuration = Date.now() - flowStartTimeRef.current;
                trackClaimFlowCompleted(
                    locationId,
                    claimToken,
                    "claim_dialog",
                    !!googleBusinessLink.trim(),
                    flowDuration
                );
            }
            
            // Reset form on success
            setGoogleBusinessLink("");
        } catch (err: any) {
            const errorMessage = err?.message || "Fout bij indienen van claim";
            setError(errorMessage);
            toast.error(errorMessage);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="google-business-link">
                    Google Business Link (optioneel)
                </Label>
                <Input
                    id="google-business-link"
                    type="url"
                    placeholder="https://g.page/..."
                    value={googleBusinessLink}
                    onChange={(e) => {
                        setGoogleBusinessLink(e.target.value);
                        setError(null);
                    }}
                    disabled={isSubmitting}
                    className={error ? "border-red-500" : ""}
                />
                <p className="text-xs text-muted-foreground">
                    Link naar je Google Business profiel (optioneel)
                </p>
            </div>

            {error && (
                <div className="text-sm text-red-500">{error}</div>
            )}

            <div className="flex justify-end gap-2">
                <Button
                    type="submit"
                    disabled={isSubmitting || !googleBusinessLink.trim()}
                >
                    {isSubmitting ? "Indienen..." : "Indienen"}
                </Button>
            </div>
        </form>
    );
}

