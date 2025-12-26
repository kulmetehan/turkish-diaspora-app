import { useState } from "react";
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

type Props = {
    location: LocationMarker;
    open: boolean;
    onClose: () => void;
    onSuccess?: () => void;
};

export function ClaimDialog({ location, open, onClose, onSuccess }: Props) {
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (data: { google_business_link?: string }) => {
        setIsSubmitting(true);
        try {
            await submitClaim(parseInt(location.id), data);
            toast.success("Claim succesvol ingediend! We zullen je claim zo snel mogelijk beoordelen.");
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
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent 
                className="sm:max-w-[500px] z-[80]"
                overlayClassName="z-[79]"
            >
                <DialogHeader>
                    <DialogTitle>Claim {location.name}</DialogTitle>
                </DialogHeader>
                <ClaimForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
            </DialogContent>
        </Dialog>
    );
}

