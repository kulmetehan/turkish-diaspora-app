import EditLocationDialog from "@/components/admin/EditLocationDialog";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { listAdminLocations, retireAdminLocation, type AdminLocationListItem } from "@/lib/apiAdmin";
import { supabase } from "@/lib/supabaseClient";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

const STATES = ["ALL", "VERIFIED", "CANDIDATE", "PENDING_VERIFICATION", "RETIRED"] as const;

export default function AdminLocationsTable() {
    const [search, setSearch] = useState("");
    const [stateFilter, setStateFilter] = useState<(typeof STATES)[number]>("ALL");
    const [limit, setLimit] = useState(20);
    const [offset, setOffset] = useState(0);
    const [rows, setRows] = useState<AdminLocationListItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const nav = useNavigate();

    const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
    const pageCount = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

    async function load() {
        setLoading(true);
        try {
            const effectiveStateParam = stateFilter === "ALL" ? undefined : stateFilter;
            const res = await listAdminLocations({ search, state: effectiveStateParam, limit, offset });
            setRows(res.rows);
            setTotal(res.total);
        } catch (e: any) {
            if (e?.message?.includes("401") || e?.message?.includes("403") || e?.message?.startsWith?.("AUTH_")) {
                await supabase.auth.signOut();
                nav("/login", { replace: true });
            } else {
                if (import.meta.env.DEV) {
                    // eslint-disable-next-line no-console
                    console.error("Failed to load admin locations", e);
                }
                toast.error(e?.message || "Kon data niet laden");
            }
            // Reset table to empty on error to avoid spinner loop
            setRows([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { void load(); }, [search, stateFilter, limit, offset]);

    const canPrev = offset > 0;
    const canNext = offset + limit < total;

    return (
        <Card>
            <CardContent className="p-4 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                    <div className="flex-1 min-w-[220px]">
                        <Input placeholder="Zoek op naam of adres…" value={search} onChange={e => { setOffset(0); setSearch(e.target.value); }} />
                    </div>
                    <Select value={stateFilter} onValueChange={(val) => { setOffset(0); setStateFilter(val as any); }}>
                        <SelectTrigger className="w-[220px]">{stateFilter === "ALL" ? "All" : stateFilter}</SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All</SelectItem>
                            <SelectItem value="VERIFIED">VERIFIED</SelectItem>
                            <SelectItem value="CANDIDATE">CANDIDATE</SelectItem>
                            <SelectItem value="PENDING_VERIFICATION">PENDING_VERIFICATION</SelectItem>
                            <SelectItem value="RETIRED">RETIRED</SelectItem>
                        </SelectContent>
                    </Select>
                    <div className="ml-auto flex items-center gap-2">
                        <Button variant="outline" size="sm" disabled={!canPrev || loading} onClick={() => setOffset(Math.max(0, offset - limit))}><Icon name="ChevronLeft" className="h-4 w-4" /></Button>
                        <span className="text-sm text-muted-foreground">Pagina {page} / {pageCount}</span>
                        <Button variant="outline" size="sm" disabled={!canNext || loading} onClick={() => setOffset(offset + limit)}><Icon name="ChevronRight" className="h-4 w-4" /></Button>
                    </div>
                </div>

                <div className="overflow-auto">
                    <table className="w-full text-sm">
                        <thead className="text-left text-muted-foreground border-b">
                            <tr>
                                <th className="py-2 pr-3">ID</th>
                                <th className="py-2 pr-3">Name</th>
                                <th className="py-2 pr-3">Category</th>
                                <th className="py-2 pr-3">State</th>
                                <th className="py-2 pr-3">Confidence</th>
                                <th className="py-2 pr-3">Last Verified</th>
                                <th className="py-2 pr-3">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map(r => (
                                <tr key={r.id} className="border-b last:border-0 hover:bg-muted/30">
                                    <td className="py-2 pr-3 whitespace-nowrap">{r.id}</td>
                                    <td className="py-2 pr-3">{r.name}</td>
                                    <td className="py-2 pr-3">{r.category || "—"}</td>
                                    <td className="py-2 pr-3">{r.state}</td>
                                    <td className="py-2 pr-3">{r.confidence_score ?? "—"}</td>
                                    <td className="py-2 pr-3">{r.last_verified_at ? new Date(r.last_verified_at).toLocaleString() : "—"}</td>
                                    <td className="py-2 pr-3">
                                        <div className="flex items-center gap-2">
                                            <Button size="sm" variant="secondary" onClick={() => setEditingId(r.id)}>
                                                <Icon name="PenSquare" className="h-4 w-4 mr-1" /> Edit
                                            </Button>
                                            <Button size="sm" variant="destructive" onClick={async () => {
                                                if (!confirm("Weet je zeker dat je deze locatie wil verbergen?")) return;
                                                try {
                                                    await retireAdminLocation(r.id);
                                                    toast("Locatie verborgen (RETired)");
                                                    void load();
                                                } catch (e: any) {
                                                    toast.error(e?.message || "Kon locatie niet verbergen");
                                                }
                                            }}>
                                                <Icon name="Archive" className="h-4 w-4 mr-1" /> Retire
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {rows.length === 0 && !loading && (
                                <tr><td colSpan={7} className="py-6 text-center text-muted-foreground">Geen resultaten</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </CardContent>
            <EditLocationDialog id={editingId} open={editingId !== null} onOpenChange={(o) => { if (!o) setEditingId(null); }} onSaved={() => void load()} />
        </Card>
    );
}


