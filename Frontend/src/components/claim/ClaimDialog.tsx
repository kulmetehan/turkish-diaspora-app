import { useState, useEffect, useRef } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { ClaimForm } from "./ClaimForm";
import type { LocationMarker } from "@/api/fetchLocations";
import { submitClaim } from "@/lib/api";
import { toast } from "sonner";
import {
    trackClaimFlowStarted,
    trackClaimFlowAbandoned,
} from "@/lib/analytics";

type Props = {
    location: LocationMarker;
    open: boolean;
    onClose: () => void;
    onSuccess?: () => void;
};

export function ClaimDialog({ location, open, onClose, onSuccess }: Props) {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const flowStartTimeRef = useRef<number | null>(null);
    const locationId = parseInt(location.id);
    // Use a dummy token for dialog tracking (claim_token is only available in ClaimPage)
    const claimToken = `dialog_${locationId}_${Date.now()}`;

    // Track flow started when dialog opens
    useEffect(() => {
        if (open) {
            flowStartTimeRef.current = Date.now();
            trackClaimFlowStarted(locationId, claimToken, "claim_dialog");
        }
    }, [open, locationId, claimToken]);

    // Track flow abandoned when dialog closes without submit
    const handleClose = (open: boolean) => {
        if (!open && flowStartTimeRef.current && !isSubmitting) {
            const flowDuration = Date.now() - flowStartTimeRef.current;
            trackClaimFlowAbandoned(
                locationId,
                claimToken,
                "claim_dialog",
                "dialog_closed",
                flowDuration
            );
            flowStartTimeRef.current = null;
        }
        onClose();
    };

    const handleSubmit = async (data: { google_business_link?: string }) => {
        setIsSubmitting(true);
        try {
            await submitClaim(parseInt(location.id), data);
            toast.success("Claim succesvol ingediend! We zullen je claim zo snel mogelijk beoordelen.");
            // Note: claim_flow_completed is tracked in ClaimForm
            onClose();
            if (onSuccess) {
                onSuccess();
            }
        } catch (err: any) {
            const errorMessage = err?.message || "Fout bij indienen van claim";
            toast.error(errorMessage);
            throw err; // Re-throw to let ClaimForm handle it
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent 
                className="sm:max-w-[500px] z-[80]"
                overlayClassName="z-[79]"
            >
                <DialogHeader>
                    <DialogTitle>Claim {location.name}</DialogTitle>
                </DialogHeader>
                <ClaimForm 
                    onSubmit={handleSubmit} 
                    isSubmitting={isSubmitting}
                    locationId={locationId}
                    claimToken={claimToken}
                />
            </DialogContent>
        </Dialog>
    );
}

