import AdminAddLocationDialog from "@/components/admin/AdminAddLocationDialog";
import EditLocationDialog from "@/components/admin/EditLocationDialog";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { bulkUpdateLocations, listAdminLocationCategories, listAdminLocations, listLocationStates, retireAdminLocation, type AdminLocationListItem } from "@/lib/apiAdmin";
import type { CategoryOption } from "@/api/fetchLocations";
import { supabase } from "@/lib/supabaseClient";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useVirtualizer } from "@tanstack/react-virtual";
import { loadAdminLocationFilters, saveAdminLocationFilters } from "@/lib/adminFilterStorage";

const DEFAULT_STATE_OPTIONS = [
    { value: "VERIFIED", label: "Verified" },
    { value: "PENDING_VERIFICATION", label: "Pending Verification" },
    { value: "CANDIDATE", label: "Candidate" },
    { value: "RETIRED", label: "Retired" },
] as const;

type StateOption = { value: string; label: string };

type ColumnDef = {
    id: string;
    label: string;
    headerClassName: string;
    cellClassName: string;
};

const COLUMNS: ColumnDef[] = [
    {
        id: "select",
        label: "",
        headerClassName: "w-12 px-2 py-2 text-center",
        cellClassName: "w-12 px-2 py-2 text-center",
    },
    {
        id: "id",
        label: "ID",
        headerClassName: "w-16 px-2 py-2 text-right font-medium",
        cellClassName: "w-16 px-2 py-2 text-right",
    },
    {
        id: "name",
        label: "Name",
        headerClassName: "min-w-[200px] px-3 py-2 text-left font-medium",
        cellClassName: "min-w-[200px] px-3 py-2 text-left",
    },
    {
        id: "category",
        label: "Category",
        headerClassName: "w-32 px-2 py-2 text-left font-medium",
        cellClassName: "w-32 px-2 py-2 text-left",
    },
    {
        id: "state",
        label: "State",
        headerClassName: "w-40 px-2 py-2 text-left font-medium",
        cellClassName: "w-40 px-2 py-2 text-left",
    },
    {
        id: "confidence",
        label: "Confidence",
        headerClassName: "w-24 px-2 py-2 text-right font-medium",
        cellClassName: "w-24 px-2 py-2 text-right",
    },
    {
        id: "lastVerified",
        label: "Last Verified",
        headerClassName: "w-40 px-2 py-2 text-right font-medium",
        cellClassName: "w-40 px-2 py-2 text-right",
    },
    {
        id: "actions",
        label: "Actions",
        headerClassName: "w-40 px-3 py-2 text-right font-medium",
        cellClassName: "w-40 px-3 py-2 text-right",
    },
];

export default function AdminLocationsTable() {
    // Load persisted filters on mount
    const savedFilters = loadAdminLocationFilters();
    
    const [search, setSearch] = useState(savedFilters.search ?? "");
    const [stateFilter, setStateFilter] = useState<string>(savedFilters.stateFilter ?? "ALL");
    const [limit, setLimit] = useState(savedFilters.limit ?? 100);
    const [offset, setOffset] = useState(savedFilters.offset ?? 0);
    const [rows, setRows] = useState<AdminLocationListItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [selected, setSelected] = useState<Set<number>>(new Set());
    const [stateOptions, setStateOptions] = useState<StateOption[]>(() => [...DEFAULT_STATE_OPTIONS]);
    const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
    const [categoryFilter, setCategoryFilter] = useState<string>(savedFilters.categoryFilter ?? "ALL");
    const [sort, setSort] = useState<"NONE" | "latest_added" | "latest_verified">(savedFilters.sort ?? "NONE");
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">(savedFilters.sortDirection ?? "desc");
    const [confidenceMin, setConfidenceMin] = useState<string>(savedFilters.confidenceMin ?? "");
    const [confidenceMax, setConfidenceMax] = useState<string>(savedFilters.confidenceMax ?? "");
    const [bulkLoading, setBulkLoading] = useState(false);
    const [bulkUnretire, setBulkUnretire] = useState(false);
    const [isOptionsLoading, setIsOptionsLoading] = useState(true);
    const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
    const nav = useNavigate();

    const parseConfidence = (value: string): number | undefined => {
        if (value.trim() === "") return undefined;
        const parsed = Number(value);
        if (Number.isNaN(parsed)) return undefined;
        return Math.max(0, Math.min(1, parsed));
    };

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
            const effectiveCategoryParam = categoryFilter === "ALL" ? undefined : categoryFilter;
            const params: {
                search?: string;
                state?: string;
                category?: string;
                confidenceMin?: number;
                confidenceMax?: number;
                sort?: string;
                sortDirection?: "asc" | "desc";
                limit?: number;
                offset?: number;
            } = {
                search,
                state: effectiveStateParam,
                category: effectiveCategoryParam,
                confidenceMin: parseConfidence(confidenceMin),
                confidenceMax: parseConfidence(confidenceMax),
                limit,
                offset,
            };
            if (sort !== "NONE") {
                params.sort = sort;
                params.sortDirection = sortDirection;
            }
            const res = await listAdminLocations(params);
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
        setIsOptionsLoading(true);
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
                toast.warning("Kon statussen niet laden, gebruik standaardopties.");
            })
            .finally(() => {
                if (!cancelled) {
                    setIsOptionsLoading(false);
                }
            });

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let cancelled = false;
        listAdminLocationCategories()
            .then((cats) => {
                if (cancelled) return;
                setCategoryOptions(cats);
                setCategoryFilter((prev) => {
                    if (prev !== "ALL" && !cats.some((cat) => cat.key === prev)) {
                        return "ALL";
                    }
                    return prev;
                });
            })
            .catch(() => {
                if (cancelled) return;
                setCategoryOptions([]);
                setCategoryFilter("ALL");
                toast.error("Kon categorieën niet laden.");
            });
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => { void load(); }, [search, stateFilter, categoryFilter, confidenceMin, confidenceMax, sort, sortDirection, limit, offset]);

    // Save filters to localStorage with debounce
    useEffect(() => {
        const timeoutId = setTimeout(() => {
            saveAdminLocationFilters({
                search,
                stateFilter,
                categoryFilter,
                confidenceMin,
                confidenceMax,
                sort,
                sortDirection,
                limit,
                offset,
            });
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [search, stateFilter, categoryFilter, confidenceMin, confidenceMax, sort, sortDirection, limit, offset]);

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
            toast.error(e?.message || "Bulkactie mislukt. Probeer het later opnieuw.");
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
                toast.success(`${selectedIds.length} locaties succesvol geverifieerd.`);
                return;
            }
            if (ok === 0) {
                toast.warning("Geen locaties geverifieerd. Schakel 'Unretire & Verify' in om gepensioneerde locaties op te nemen.");
            } else if (blocked > 0) {
                toast.warning(`${ok} van ${total} locaties geverifieerd. ${blocked} vereisen 'Unretire & Verify'.`);
            } else {
                toast.success(`${ok} locaties succesvol geverifieerd.`);
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
            toast.success(`${selectedIds.length} locaties succesvol met pensioen gezet.`);
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
            toast.success(`${selectedIds.length} locaties: confidence score aangepast naar ${value}.`);
        });
    };

    const canPrev = offset > 0;
    const canNext = offset + limit < total;
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    const virtualizer = useVirtualizer({
        count: rows.length,
        getScrollElement: () => scrollContainerRef.current,
        estimateSize: () => 50,
        overscan: 5,
    });

    const handleLocationCreated = () => {
        toast.success("Locatie succesvol aangemaakt.");
        setIsAddDialogOpen(false);
        setOffset(0);
        void load();
    };

    return (
        <Card className="max-h-[80vh]">
            <CardContent className="p-4 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <Button onClick={() => setIsAddDialogOpen(true)}>
                        <Icon name="Plus" className="mr-2 h-4 w-4" />
                        Locatie toevoegen
                    </Button>
                    <span className="text-sm text-muted-foreground">
                        {total} resultaten
                    </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <div className="flex-1 min-w-[220px]">
                        <Input placeholder="Zoek op naam of adres…" value={search} onChange={e => { setOffset(0); setSearch(e.target.value); }} />
                    </div>
                    <Select value={stateFilter} onValueChange={(val) => { setOffset(0); setStateFilter(val); }} disabled={isOptionsLoading}>
                        <SelectTrigger className="w-[220px]">
                            <SelectValue placeholder={isOptionsLoading ? "Laden..." : "All states"} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All</SelectItem>
                            {stateOptions.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={categoryFilter} onValueChange={(val) => { setOffset(0); setCategoryFilter(val); }} disabled={isOptionsLoading}>
                        <SelectTrigger className="w-[220px]">
                            <SelectValue placeholder={isOptionsLoading ? "Laden..." : categoryOptions.length > 0 ? "Categorie" : "Geen categorieën"} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">All categories</SelectItem>
                            {categoryOptions.map((cat) => (
                                <SelectItem key={cat.key} value={cat.key}>{cat.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={sort} onValueChange={(val) => { setOffset(0); setSort(val as typeof sort); }}>
                        <SelectTrigger className="w-[200px]">
                            <SelectValue placeholder="Sortering" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="NONE">Geen sortering</SelectItem>
                            <SelectItem value="latest_added">Laatst toegevoegd</SelectItem>
                            <SelectItem value="latest_verified">Laatst geverifieerd</SelectItem>
                        </SelectContent>
                    </Select>
                    {sort !== "NONE" && (
                        <Select value={sortDirection} onValueChange={(val) => { setOffset(0); setSortDirection(val as typeof sortDirection); }}>
                            <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="Richting" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="desc">Nieuwste eerst</SelectItem>
                                <SelectItem value="asc">Oudste eerst</SelectItem>
                            </SelectContent>
                        </Select>
                    )}
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground">Confidence min (0-1)</span>
                        <Input
                            type="number"
                            step="0.05"
                            min={0}
                            max={1}
                            value={confidenceMin}
                            onChange={(e) => { setOffset(0); setConfidenceMin(e.target.value); }}
                            placeholder="Min"
                            className="w-24"
                        />
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground">Confidence max (0-1)</span>
                        <Input
                            type="number"
                            step="0.05"
                            min={0}
                            max={1}
                            value={confidenceMax}
                            onChange={(e) => { setOffset(0); setConfidenceMax(e.target.value); }}
                            placeholder="Max"
                            className="w-24"
                        />
                    </div>
                    <div className="ml-auto flex items-center gap-2">
                        <Button variant="outline" size="sm" disabled={!canPrev || loading} onClick={() => setOffset(Math.max(0, offset - limit))}><Icon name="ChevronLeft" className="h-4 w-4" /></Button>
                        <span className="text-sm text-muted-foreground">Pagina {page} / {pageCount}</span>
                        <Button variant="outline" size="sm" disabled={!canNext || loading} onClick={() => setOffset(offset + limit)}><Icon name="ChevronRight" className="h-4 w-4" /></Button>
                    </div>
                </div>

                <div ref={scrollContainerRef} className="relative h-[60vh] min-h-[360px] overflow-auto rounded-md border">
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
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm min-w-[800px] table-fixed">
                            <thead className="sticky top-0 z-20 bg-background text-muted-foreground border-b">
                                <tr className="divide-x divide-border">
                                    {COLUMNS.map((col) => (
                                        <th key={col.id} className={col.headerClassName}>
                                            {col.id === "select" ? (
                                                <input
                                                    type="checkbox"
                                                    checked={allChecked}
                                                    aria-checked={allChecked}
                                                    onChange={toggleAll}
                                                    aria-label="Selecteer alles"
                                                    className="cursor-pointer"
                                                />
                                            ) : (
                                                col.label
                                            )}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                        <tbody style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
                            {rows.length === 0 && !loading ? (
                                <tr>
                                    <td colSpan={8} className="px-2 py-6 text-center text-muted-foreground">Geen resultaten</td>
                                </tr>
                            ) : (
                                virtualizer.getVirtualItems().map((virtualRow) => {
                                    const r = rows[virtualRow.index];
                                    return (
                                        <tr
                                            key={r.id}
                                            style={{
                                                position: "absolute",
                                                top: 0,
                                                left: 0,
                                                width: "100%",
                                                transform: `translateY(${virtualRow.start}px)`,
                                            }}
                                            className="border-b hover:bg-muted/30 divide-x divide-border"
                                        >
                                            {COLUMNS.map((col) => {
                                                if (col.id === "select") {
                                                    return (
                                                        <td key={col.id} className={col.cellClassName}>
                                                            <input
                                                                type="checkbox"
                                                                checked={selected.has(r.id)}
                                                                onChange={() => toggleOne(r.id)}
                                                                aria-label={`Selecteer locatie ${r.name}`}
                                                                className="cursor-pointer"
                                                            />
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "id") {
                                                    return (
                                                        <td key={col.id} className={`${col.cellClassName} whitespace-nowrap text-muted-foreground`}>
                                                            {r.id}
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "name") {
                                                    return (
                                                        <td key={col.id} className={col.cellClassName}>
                                                            <div className="truncate" title={r.name}>
                                                                {r.name}
                                                            </div>
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "category") {
                                                    return (
                                                        <td key={col.id} className={col.cellClassName}>
                                                            <div className="truncate" title={r.category || undefined}>
                                                                {r.category || "—"}
                                                            </div>
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "state") {
                                                    return (
                                                        <td key={col.id} className={col.cellClassName}>
                                                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-muted">
                                                                {r.state}
                                                            </span>
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "confidence") {
                                                    return (
                                                        <td key={col.id} className={`${col.cellClassName} whitespace-nowrap`}>
                                                            {r.confidence_score != null ? r.confidence_score.toFixed(2) : "—"}
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "lastVerified") {
                                                    return (
                                                        <td key={col.id} className={col.cellClassName}>
                                                            <div className="truncate" title={r.last_verified_at ? new Date(r.last_verified_at).toLocaleString() : undefined}>
                                                                {r.last_verified_at ? new Date(r.last_verified_at).toLocaleString() : "—"}
                                                            </div>
                                                        </td>
                                                    );
                                                }
                                                if (col.id === "actions") {
                                                    return (
                                                        <td key={col.id} className={col.cellClassName}>
                                                            <div className="flex items-center justify-end gap-1.5">
                                                                <Button size="sm" variant="secondary" onClick={() => setEditingId(r.id)} className="h-7 px-2 text-xs">
                                                                    <Icon name="PenSquare" className="h-3.5 w-3.5 mr-1" /> Edit
                                                                </Button>
                                                                <Button size="sm" variant="destructive" onClick={async () => {
                                                                    if (!confirm("Weet je zeker dat je deze locatie wil verbergen?")) return;
                                                                    try {
                                                                        await retireAdminLocation(r.id);
                                                                        toast.success("Locatie succesvol met pensioen gezet.");
                                                                        void load();
                                                                    } catch (e: any) {
                                                                        toast.error(e?.message || "Kon locatie niet met pensioen zetten.");
                                                                    }
                                                                }} className="h-7 px-2 text-xs">
                                                                    <Icon name="Archive" className="h-3.5 w-3.5 mr-1" /> Retire
                                                                </Button>
                                                            </div>
                                                        </td>
                                                    );
                                                }
                                                return null;
                                            })}
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                    </div>
                </div>
            </CardContent>
            <EditLocationDialog id={editingId} open={editingId !== null} onOpenChange={(o) => { if (!o) setEditingId(null); }} onSaved={() => void load()} />
            <AdminAddLocationDialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen} onCreated={handleLocationCreated} />
        </Card>
    );
}


