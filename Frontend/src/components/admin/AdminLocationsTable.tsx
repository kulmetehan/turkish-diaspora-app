import EditLocationDialog from "@/components/admin/EditLocationDialog";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { bulkUpdateLocations, listAdminLocations, listLocationStates, retireAdminLocation, type AdminLocationListItem } from "@/lib/apiAdmin";
import { supabase } from "@/lib/supabaseClient";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

const DEFAULT_STATE_OPTIONS = [
    { value: "VERIFIED", label: "Verified" },
    { value: "PENDING_VERIFICATION", label: "Pending Verification" },
    { value: "CANDIDATE", label: "Candidate" },
    { value: "RETIRED", label: "Retired" },
] as const;

type StateOption = { value: string; label: string };

export default function AdminLocationsTable() {
    const [search, setSearch] = useState("");
    const [stateFilter, setStateFilter] = useState<string>("ALL");
    const [limit, setLimit] = useState(20);
    const [offset, setOffset] = useState(0);
    const [rows, setRows] = useState<AdminLocationListItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [selected, setSelected] = useState<Set<number>>(new Set());
    const [stateOptions, setStateOptions] = useState<StateOption[]>(() => [...DEFAULT_STATE_OPTIONS]);
    const [bulkLoading, setBulkLoading] = useState(false);
    const [bulkUnretire, setBulkUnretire] = useState(false);
    const nav = useNavigate();

    const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
    const pageCount = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);
    const allChecked = useMemo(() => rows.length > 0 && selected.size === rows.length, [rows, selected]);
    const hasRetiredSelection = useMemo(
        () =>
            rows.some(
                (row) =>
                    selected.has(row.id) &&
                    ((row.state ?? "").toUpperCase() === "RETIRED" || Boolean(row.is_retired)),
            ),
        [rows, selected],
    );

    async function load() {
        setLoading(true);
        try {
            const effectiveStateParam = stateFilter === "ALL" ? undefined : stateFilter;
            const res = await listAdminLocations({ search, state: effectiveStateParam, limit, offset });
            setRows(res.rows);
            setTotal(res.total);
            setSelected(new Set());
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

    useEffect(() => {
        let cancelled = false;
        listLocationStates()
            .then((res) => {
                if (cancelled) return;
                if (Array.isArray(res?.states) && res.states.length > 0) {
                    setStateOptions(res.states);
                }
            })
            .catch(() => {
                if (cancelled) return;
                setStateOptions([...DEFAULT_STATE_OPTIONS]);
            });

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => { void load(); }, [search, stateFilter, limit, offset]);

    useEffect(() => {
        setSelected((prev) => {
            if (prev.size === 0) return prev;
            const validIds = new Set(rows.map((r) => r.id));
            const next = new Set<number>();
            prev.forEach((id) => {
                if (validIds.has(id)) next.add(id);
            });
            return next;
        });
    }, [rows]);

    useEffect(() => {
        if (!hasRetiredSelection) {
            setBulkUnretire(false);
        }
    }, [hasRetiredSelection]);

    const toggleAll = () => {
        setSelected((prev) => {
            if (rows.length === 0) return prev;
            if (prev.size === rows.length) {
                return new Set();
            }
            return new Set(rows.map((r) => r.id));
        });
    };

    const toggleOne = (id: number) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const selectedRows = useMemo(() => rows.filter((row) => selected.has(row.id)), [rows, selected]);
    const selectedIds = useMemo(() => selectedRows.map((row) => row.id), [selectedRows]);
    const retiredIds = useMemo(
        () => selectedRows.filter((row) => Boolean(row.is_retired)).map((row) => row.id),
        [selectedRows],
    );
    const eligibleIds = useMemo(
        () => selectedRows.filter((row) => !row.is_retired).map((row) => row.id),
        [selectedRows],
    );

    const runBulkAction = async (action: () => Promise<void>, onSuccess?: () => void) => {
        if (selectedIds.length === 0) return;
        try {
            setBulkLoading(true);
            await action();
            onSuccess?.();
            setSelected(new Set());
            await load();
        } catch (e: any) {
            toast.error(e?.message || "Bulkactie mislukt");
        } finally {
            setBulkLoading(false);
        }
    };

    const handleBulkVerify = async () => {
        const total = selectedRows.length;
        const shouldForce = bulkUnretire;
        const ok = shouldForce ? total : eligibleIds.length;
        const blocked = shouldForce ? 0 : retiredIds.length;

        await runBulkAction(async () => {
            if (shouldForce) {
                await bulkUpdateLocations({
                    ids: selectedIds,
                    action: { type: "verify", force: true, clear_retired: true },
                });
                setBulkUnretire(false);
                return;
            }
            if (eligibleIds.length === 0) {
                return;
            }
            await bulkUpdateLocations({ ids: eligibleIds, action: { type: "verify" } });
        }, () => {
            if (shouldForce) {
                toast.success("Selected locations verified.");
                return;
            }
            if (ok === 0) {
                toast.warning("No locations verified. Enable 'Unretire & Verify' to include retired ones.");
            } else if (blocked > 0) {
                toast.success(`${ok} of ${total} locations verified. ${blocked} require 'Unretire & Verify'.`);
            } else {
                toast.success("Selected locations verified.");
            }
        });
    };

    const handleBulkRetire = async () => {
        await runBulkAction(async () => {
            await bulkUpdateLocations({ ids: selectedIds, action: { type: "retire" } });
            setRows((prevRows) =>
                prevRows.map((row) =>
                    selected.has(row.id)
                        ? { ...row, state: "RETIRED", is_retired: true }
                        : row,
                ),
            );
        }, () => {
            toast.success("Geselecteerde locaties verborgen (RETired)");
        });
    };

    const handleBulkConfidence = async () => {
        const raw = window.prompt("Set confidence (0.0 - 1.0):", "0.9");
        if (raw === null) return;
        const value = Number(raw);
        if (Number.isNaN(value) || value < 0 || value > 1) {
            toast.error("Ongeldige waarde. Voer een getal tussen 0 en 1 in.");
            return;
        }
        await runBulkAction(async () => {
            await bulkUpdateLocations({ ids: selectedIds, action: { type: "adjust_confidence", value } });
            setRows((prevRows) =>
                prevRows.map((row) => (selected.has(row.id) ? { ...row, confidence_score: value } : row))
            );
        }, () => {
            toast.success("Confidence aangepast");
        });
    };

    const canPrev = offset > 0;
    const canNext = offset + limit < total;
    return (
        <Card className="max-h-[80vh]">
            <CardContent className="p-4 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                    <div className="flex-1 min-w-[220px]">
                        <Input placeholder="Zoek op naam of adres…" value={search} onChange={e => { setOffset(0); setSearch(e.target.value); }} />
                    </div>
                    <Select value={stateFilter} onValueChange={(val) => { setOffset(0); setStateFilter(val); }}>
                        <SelectTrigger className="w-[220px]">
                            <SelectValue placeholder="All states" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All</SelectItem>
                            {stateOptions.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <div className="ml-auto flex items-center gap-2">
                        <Button variant="outline" size="sm" disabled={!canPrev || loading} onClick={() => setOffset(Math.max(0, offset - limit))}><Icon name="ChevronLeft" className="h-4 w-4" /></Button>
                        <span className="text-sm text-muted-foreground">Pagina {page} / {pageCount}</span>
                        <Button variant="outline" size="sm" disabled={!canNext || loading} onClick={() => setOffset(offset + limit)}><Icon name="ChevronRight" className="h-4 w-4" /></Button>
                    </div>
                </div>

                <div className="relative h-[60vh] min-h-[360px] overflow-auto rounded-md border">
                    {selected.size > 0 && (
                        <div className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background/90 px-4 py-2 text-sm backdrop-blur">
                            <span>{selected.size} geselecteerd</span>
                            <Button size="sm" onClick={() => void handleBulkVerify()} disabled={bulkLoading}>
                                <Icon name="ShieldCheck" className="mr-2 h-4 w-4" />
                                Verify
                            </Button>
                            {hasRetiredSelection && (
                                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        checked={bulkUnretire}
                                        onChange={(e) => setBulkUnretire(e.target.checked)}
                                        disabled={bulkLoading}
                                    />
                                    Unretire &amp; Verify
                                </label>
                            )}
                            <Button size="sm" variant="destructive" onClick={() => void handleBulkRetire()} disabled={bulkLoading}>
                                <Icon name="Archive" className="mr-2 h-4 w-4" />
                                Retire
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => void handleBulkConfidence()} disabled={bulkLoading}>
                                <Icon name="Activity" className="mr-2 h-4 w-4" />
                                Adjust Confidence
                            </Button>
                            <Button
                                size="sm"
                                variant="ghost"
                                className="ml-auto"
                                onClick={() => {
                                    setSelected(new Set());
                                    setBulkUnretire(false);
                                }}
                                disabled={bulkLoading}
                            >
                                Clear
                            </Button>
                        </div>
                    )}
                    <table className="w-full text-sm">
                        <thead className="text-left text-muted-foreground border-b">
                            <tr>
                                <th className="w-12 px-4 py-2">
                                    <input
                                        type="checkbox"
                                        checked={allChecked}
                                        aria-checked={allChecked}
                                        onChange={toggleAll}
                                        aria-label="Selecteer alles"
                                    />
                                </th>
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
                                    <td className="px-4 py-2">
                                        <input
                                            type="checkbox"
                                            checked={selected.has(r.id)}
                                            onChange={() => toggleOne(r.id)}
                                            aria-label={`Selecteer locatie ${r.name}`}
                                        />
                                    </td>
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


