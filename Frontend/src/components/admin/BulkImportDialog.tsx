import { useEffect, useState, type ChangeEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { bulkImportLocations, type AdminLocationBulkImportResult } from "@/lib/apiAdmin";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onImported: () => void;
};

export default function BulkImportDialog({ open, onOpenChange, onImported }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<AdminLocationBulkImportResult | null>(null);
    const [error, setError] = useState<string>("");

    useEffect(() => {
        if (!open) {
            // Reset state when dialog closes
            setFile(null);
            setResult(null);
            setError("");
        }
    }, [open]);

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0] || null;
        setFile(selectedFile);
        setResult(null);
        setError("");
    };

    const validateCSVHeaders = (file: File): Promise<{ valid: boolean; headers: string[]; error?: string }> => {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const text = e.target?.result as string;
                    // Remove UTF-8 BOM if present
                    const cleanText = text.replace(/^\uFEFF/, "");
                    const lines = cleanText.split(/\r?\n/).filter((line) => line.trim());

                    if (lines.length === 0) {
                        resolve({ valid: false, headers: [], error: "CSV bestand is leeg" });
                        return;
                    }

                    // Parse first line as headers
                    const headerLine = lines[0];
                    const headers = headerLine.split(",").map((h) => h.trim().toLowerCase());

                    const required = ["name", "address", "lat", "lng", "category"];
                    const missing = required.filter((col) => !headers.includes(col));

                    if (missing.length > 0) {
                        resolve({
                            valid: false,
                            headers,
                            error: `Ontbrekende kolommen: ${missing.join(", ")}. Gevonden headers: ${headers.join(", ")}`,
                        });
                        return;
                    }

                    resolve({ valid: true, headers });
                } catch (err) {
                    resolve({
                        valid: false,
                        headers: [],
                        error: `Fout bij lezen van CSV: ${err instanceof Error ? err.message : String(err)}`,
                    });
                }
            };
            reader.onerror = () => {
                resolve({ valid: false, headers: [], error: "Kon bestand niet lezen" });
            };
            reader.readAsText(file, "utf-8");
        });
    };

    const handleSubmit = async () => {
        if (!file) {
            toast.error("Selecteer eerst een CSV-bestand.");
            return;
        }

        // Validate file type
        if (!file.name.endsWith(".csv") && file.type !== "text/csv") {
            toast.error("Selecteer een geldig CSV-bestand.");
            return;
        }

        setLoading(true);
        setError("");
        setResult(null);

        try {
            // Validate CSV headers before upload
            const validation = await validateCSVHeaders(file);
            if (!validation.valid) {
                setError(validation.error || "CSV validatie mislukt");
                toast.error(validation.error || "CSV validatie mislukt");
                setLoading(false);
                return;
            }

            // Proceed with upload
            const importResult = await bulkImportLocations(file);
            setResult(importResult);

            if (importResult.rows_failed === 0) {
                toast.success(`${importResult.rows_created} locaties succesvol geïmporteerd.`);
                onImported();
                onOpenChange(false);
            } else if (importResult.rows_created > 0) {
                toast.warning(
                    `${importResult.rows_created} locaties geïmporteerd, ${importResult.rows_failed} gefaald.`
                );
                onImported();
            } else {
                toast.error(`Import mislukt: alle ${importResult.rows_failed} rijen hebben gefaald.`);
            }
        } catch (err: any) {
            const errorMessage = err?.message || "Kon bestand niet importeren. Probeer het later opnieuw.";
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(value) => onOpenChange(value)}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Bulk import locaties (CSV)</DialogTitle>
                    <DialogDescription>
                        Upload een CSV-bestand met kolommen: <strong>name</strong>, <strong>address</strong>,{" "}
                        <strong>lat</strong>, <strong>lng</strong>, <strong>category</strong>, <strong>notes</strong>{" "}
                        (optioneel), <strong>evidence_urls</strong> (optioneel, komma-gescheiden).
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="bulk-import-file">CSV Bestand</Label>
                        <Input
                            id="bulk-import-file"
                            type="file"
                            accept=".csv,text/csv"
                            onChange={handleFileChange}
                            disabled={loading}
                        />
                        {file && (
                            <p className="text-sm text-muted-foreground">
                                Geselecteerd: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(2)} KB)
                            </p>
                        )}
                    </div>

                    {error && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                            <strong>Fout:</strong> {error}
                        </div>
                    )}

                    {result && (
                        <div className="space-y-2 p-3 bg-gray-50 border rounded">
                            <div className="text-sm font-semibold">Import Resultaten:</div>
                            <div className="text-sm space-y-1">
                                <div>Totaal aantal rijen: {result.rows_total}</div>
                                <div>Verwerkt: {result.rows_processed}</div>
                                <div className="text-green-600">Aangemaakt: {result.rows_created}</div>
                                {result.rows_failed > 0 && (
                                    <div className="text-red-600">Gefaald: {result.rows_failed}</div>
                                )}
                            </div>
                            {result.errors.length > 0 && (
                                <div className="mt-3">
                                    <div className="text-sm font-semibold text-red-600">Fouten per rij:</div>
                                    <ul className="text-sm list-disc list-inside space-y-1 mt-1 max-h-48 overflow-y-auto">
                                        {result.errors.map((err, idx) => (
                                            <li key={idx}>
                                                Rij {err.row_number}: {err.message}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                            Annuleer
                        </Button>
                        <Button onClick={handleSubmit} disabled={!file || loading}>
                            {loading ? "Bezig met uploaden..." : "Upload"}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}

