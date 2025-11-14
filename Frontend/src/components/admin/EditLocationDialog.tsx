import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getAdminLocation, listLocationStates, updateAdminLocation, type AdminLocationDetail } from "@/lib/apiAdmin";

import { useEffect, useState } from "react";
import { toast } from "sonner";

type Props = {
    id: number | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSaved: () => void;
};

type StateOption = { value: string; label: string };

const DEFAULT_STATE_OPTIONS: StateOption[] = [
    { value: "VERIFIED", label: "Verified" },
    { value: "PENDING_VERIFICATION", label: "Pending Verification" },
    { value: "CANDIDATE", label: "Candidate" },
    { value: "RETIRED", label: "Retired" },
];

export default function EditLocationDialog({ id, open, onOpenChange, onSaved }: Props) {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<AdminLocationDetail | null>(null);
    const [stateOptions, setStateOptions] = useState<StateOption[]>([]);
    const [forceVerify, setForceVerify] = useState(false);
    const [forceError, setForceError] = useState(false);

    useEffect(() => {
        let active = true;
        if (!open || !id) { setData(null); return; }
        setLoading(true);
        Promise.all([
            getAdminLocation(id),
            listLocationStates().catch(() => ({ states: DEFAULT_STATE_OPTIONS })),
        ]).then(([d, s]) => {
            if (!active) return;
            setData(d);
            const options = Array.isArray(s?.states) && s.states.length > 0 ? s.states : DEFAULT_STATE_OPTIONS;
            setStateOptions(options);
            setForceVerify(false);
            setForceError(false);
        }).catch((e) => {
            toast.error(e?.message || "Kon details niet laden");
        }).finally(() => {
            if (active) setLoading(false);
        });
        return () => { active = false; };
    }, [open, id]);

    const requiresForce =
        Boolean(data?.is_retired) && (data?.state ?? "").toUpperCase() === "VERIFIED";

    async function save() {
        if (!id || !data) return;
        if (requiresForce && !forceVerify) {
            setForceError(true);
            toast.warning("Action blocked: 'Unretire & Verify' is required for retired locations.");
            return;
        }
        setLoading(true);
        try {
            await updateAdminLocation(id, {
                name: data.name,
                address: data.address ?? undefined,
                category: data.category ?? undefined,
                state: data.state,
                confidence_score: data.confidence_score ?? undefined,
                business_status: data.business_status ?? undefined,
                is_probable_not_open_yet: data.is_probable_not_open_yet ?? undefined,
                notes: data.notes ?? undefined,
                force: requiresForce && forceVerify ? true : undefined,
            });
            if (requiresForce && forceVerify) {
                toast.success("Locatie succesvol geverifieerd.");
            } else {
                toast.success("Locatie succesvol bijgewerkt.");
            }
            onSaved();
            onOpenChange(false);
        } catch (e: any) {
            toast.error(e?.message || "Kon locatie niet opslaan.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg w-full">
                <DialogHeader>
                    <DialogTitle className="text-lg font-semibold">Edit Location</DialogTitle>
                    <DialogDescription className="text-sm text-muted-foreground">Update details for this place. Mark state = RETIRED to hide it from users.</DialogDescription>
                </DialogHeader>
                {!data ? (
                    <div className="py-8 text-center text-muted-foreground">Laden…</div>
                ) : (
                    <div className="space-y-4">
                        <div className="grid gap-3 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="name">Name</Label>
                                <Input id="name" value={data.name} onChange={e => setData({ ...data, name: e.target.value })} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="category">Category</Label>
                                <Input id="category" value={data.category || ""} onChange={e => setData({ ...data, category: e.target.value || null })} />
                            </div>
                            <div className="space-y-2 sm:col-span-2">
                                <Label htmlFor="address">Address</Label>
                                <Input id="address" value={data.address || ""} onChange={e => setData({ ...data, address: e.target.value || null })} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="state">State</Label>
                                <Select
                                    value={data.state}
                                    onValueChange={(v) => {
                                        setData(prev => prev ? { ...prev, state: v } : prev);
                                        if (v !== "VERIFIED") {
                                            setForceVerify(false);
                                            setForceError(false);
                                        } else {
                                            setForceError(false);
                                        }
                                    }}
                                >
                                    <SelectTrigger id="state">
                                        <SelectValue placeholder="Select state..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {stateOptions.length === 0 ? (
                                            <SelectItem value={data.state || "PENDING_VERIFICATION"}>{data.state || "Loading..."}</SelectItem>
                                        ) : (
                                            stateOptions.map((opt) => (
                                                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                                            ))
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                            {data.is_retired && (
                                <div className="sm:col-span-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                                    Deze locatie is momenteel retired. Gebruik \"Unretire & Verify\" om de status te herstellen.
                                </div>
                            )}
                            {requiresForce && (
                                <div className="sm:col-span-2 space-y-1">
                                    <label className="flex items-center gap-2 text-xs font-medium text-amber-900">
                                        <input
                                            type="checkbox"
                                            checked={forceVerify}
                                            onChange={(e) => {
                                                setForceVerify(e.target.checked);
                                                if (e.target.checked) {
                                                    setForceError(false);
                                                }
                                            }}
                                        />
                                        Unretire &amp; Verify
                                    </label>
                                    {forceError && !forceVerify && (
                                        <p className="text-xs font-medium text-amber-700">
                                            Enable 'Unretire & Verify' to verify this retired location.
                                        </p>
                                    )}
                                </div>
                            )}
                            <div className="space-y-2">
                                <Label htmlFor="business_status">Business Status</Label>
                                <Input id="business_status" value={data.business_status || ""} onChange={e => setData({ ...data, business_status: e.target.value || null })} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="confidence_score">Confidence Score (0–1)</Label>
                                <Input
                                    id="confidence_score"
                                    type="number"
                                    min="0"
                                    max="1"
                                    step="0.01"
                                    value={data.confidence_score ?? ""}
                                    onChange={e => {
                                        const val = e.target.value;
                                        setData({
                                            ...data,
                                            confidence_score: val === "" ? null : parseFloat(val),
                                        });
                                    }}
                                />
                                <p className="text-[10px] text-muted-foreground">
                                    Raise this if you manually verified. Locations only show to users if state is VERIFIED and confidence is high enough.
                                </p>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="is_probable_not_open_yet">Probable Not Open Yet</Label>
                                <select id="is_probable_not_open_yet" className="w-full border rounded-md h-9 px-3 bg-background" value={String(Boolean(data.is_probable_not_open_yet))} onChange={e => setData({ ...data, is_probable_not_open_yet: e.target.value === "true" })}>
                                    <option value="false">No</option>
                                    <option value="true">Yes</option>
                                </select>
                            </div>
                            <div className="space-y-2 sm:col-span-2">
                                <Label htmlFor="notes">Notes</Label>
                                <textarea id="notes" className="w-full border rounded-md p-2 bg-background" rows={4} value={data.notes || ""} onChange={e => setData({ ...data, notes: e.target.value || null })} />
                            </div>
                        </div>
                        <div className="flex justify-end gap-2 mt-6">
                            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancel</Button>
                            <Button onClick={save} disabled={loading}>Save</Button>
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}


