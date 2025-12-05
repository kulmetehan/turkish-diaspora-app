// Frontend/src/components/AdminPanel.tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_BASE, apiFetch, getAdminKey } from "@/lib/api";
import { bulkImportLocations, type AdminLocationBulkImportResult } from "@/lib/apiAdmin";
import { useState } from "react";

type CreatePayload = {
  name: string;
  address: string;
  lat: number;
  lng: number;
  category: string;
  business_status?: string;
  notes?: string | null;
  is_probable_not_open_yet?: boolean | null;
};

type UpdatePayload = Partial<CreatePayload> & {
  confidence_score?: number;
  state?: string;
};

export default function AdminPanel() {
  const [createForm, setCreateForm] = useState<CreatePayload>({
    name: "",
    address: "",
    lat: 52.0,
    lng: 5.0,
    category: "bakery",
    business_status: "OPERATIONAL",
    notes: "",
    is_probable_not_open_yet: false,
  });

  const [updateId, setUpdateId] = useState<number | "">("");
  const [updateForm, setUpdateForm] = useState<UpdatePayload>({});
  const [result, setResult] = useState<string>("");

  // Bulk import state
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkIsLoading, setBulkIsLoading] = useState(false);
  const [bulkResult, setBulkResult] = useState<AdminLocationBulkImportResult | null>(null);
  const [bulkError, setBulkError] = useState<string>("");

  async function doCreate() {
    setResult("");
    try {
      const data = await apiFetch<any>("/admin/locations", {
        method: "POST",
        headers: { "X-Admin-Key": getAdminKey() },
        body: JSON.stringify(createForm),
      });
      setResult(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setResult(e?.message ?? String(e));
    }
  }

  async function doUpdate() {
    if (!updateId || typeof updateId !== "number") {
      setResult("Vul een geldige ID in voor update.");
      return;
    }
    setResult("");
    try {
      const data = await apiFetch<any>(`/admin/locations/${updateId}`, {
        method: "PATCH",
        headers: { "X-Admin-Key": getAdminKey() },
        body: JSON.stringify(updateForm),
      });
      setResult(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setResult(e?.message ?? String(e));
    }
  }

  async function doBulkImport() {
    if (!bulkFile) {
      return;
    }
    setBulkIsLoading(true);
    setBulkError("");
    setBulkResult(null);
    try {
      const data = await bulkImportLocations(bulkFile);
      setBulkResult(data);
    } catch (e: any) {
      setBulkError(e?.message ?? String(e));
    } finally {
      setBulkIsLoading(false);
    }
  }

  function handleBulkFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] || null;
    setBulkFile(file);
    setBulkResult(null);
    setBulkError("");
  }

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Admin Panel (Locations)</h2>
        <div className="text-xs text-muted-foreground">
          API: <code>{API_BASE}</code>
        </div>
      </header>

      {/* CREATE */}
      <Card>
        <CardHeader>
          <CardTitle>Nieuwe locatie aanmaken</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label>Address</Label>
              <Input
                value={createForm.address}
                onChange={(e) => setCreateForm({ ...createForm, address: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label>Lat</Label>
              <Input
                type="number"
                value={createForm.lat}
                onChange={(e) => setCreateForm({ ...createForm, lat: parseFloat(e.target.value) })}
              />
            </div>
            <div className="space-y-1">
              <Label>Lng</Label>
              <Input
                type="number"
                value={createForm.lng}
                onChange={(e) => setCreateForm({ ...createForm, lng: parseFloat(e.target.value) })}
              />
            </div>
            <div className="space-y-1">
              <Label>Category</Label>
              <Input
                value={createForm.category}
                onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label>Business Status</Label>
              <Input
                value={createForm.business_status || ""}
                onChange={(e) => setCreateForm({ ...createForm, business_status: e.target.value })}
              />
            </div>

            <div className="md:col-span-2 space-y-1">
              <Label>Notes</Label>
              <Input
                value={createForm.notes || ""}
                onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!createForm.is_probable_not_open_yet}
                onChange={(e) =>
                  setCreateForm({
                    ...createForm,
                    is_probable_not_open_yet: e.target.checked,
                  })
                }
              />
              Probable Not Open Yet
            </label>
          </div>

          <div className="pt-2">
            <Button onClick={doCreate}>Aanmaken</Button>
          </div>
        </CardContent>
      </Card>

      {/* BULK IMPORT */}
      <Card>
        <CardHeader>
          <CardTitle>Bulk import locations (CSV)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Upload een CSV-bestand met kolommen: <strong>name</strong>, <strong>address</strong>, <strong>lat</strong>, <strong>lng</strong>, <strong>category</strong>, <strong>notes</strong> (optioneel), <strong>evidence_urls</strong> (optioneel, komma-gescheiden).
          </p>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>CSV Bestand</Label>
              <Input
                type="file"
                accept=".csv,text/csv"
                onChange={handleBulkFileChange}
                disabled={bulkIsLoading}
              />
            </div>
            <Button
              onClick={doBulkImport}
              disabled={!bulkFile || bulkIsLoading}
            >
              {bulkIsLoading ? "Uploading..." : "Upload"}
            </Button>
          </div>

          {bulkError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
              <strong>Error:</strong> {bulkError}
            </div>
          )}

          {bulkResult && (
            <div className="space-y-2 p-3 bg-gray-50 border rounded">
              <div className="text-sm font-semibold">Import Resultaten:</div>
              <div className="text-sm space-y-1">
                <div>Total rows: {bulkResult.rows_total}</div>
                <div>Processed: {bulkResult.rows_processed}</div>
                <div className="text-green-600">Created: {bulkResult.rows_created}</div>
                {bulkResult.rows_failed > 0 && (
                  <div className="text-red-600">Failed: {bulkResult.rows_failed}</div>
                )}
              </div>
              {bulkResult.errors.length > 0 && (
                <div className="mt-3">
                  <div className="text-sm font-semibold text-red-600">Errors:</div>
                  <ul className="text-sm list-disc list-inside space-y-1 mt-1">
                    {bulkResult.errors.map((err, idx) => (
                      <li key={idx}>
                        Row {err.row_number}: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* UPDATE */}
      <Card>
        <CardHeader>
          <CardTitle>Bestaande locatie bewerken</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label>Location ID</Label>
              <Input
                value={updateId}
                onChange={(e) => setUpdateId(e.target.value ? parseInt(e.target.value) : "")}
              />
            </div>
            <div className="space-y-1">
              <Label>name</Label>
              <Input
                onChange={(e) => setUpdateForm({ ...updateForm, name: e.target.value || undefined })}
              />
            </div>
            <div className="space-y-1">
              <Label>address</Label>
              <Input
                onChange={(e) => setUpdateForm({ ...updateForm, address: e.target.value || undefined })}
              />
            </div>
            <div className="space-y-1">
              <Label>lat</Label>
              <Input
                type="number"
                onChange={(e) =>
                  setUpdateForm({
                    ...updateForm,
                    lat: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
              />
            </div>
            <div className="space-y-1">
              <Label>lng</Label>
              <Input
                type="number"
                onChange={(e) =>
                  setUpdateForm({
                    ...updateForm,
                    lng: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
              />
            </div>
            <div className="space-y-1">
              <Label>category</Label>
              <Input
                onChange={(e) =>
                  setUpdateForm({ ...updateForm, category: e.target.value || undefined })
                }
              />
            </div>
            <div className="space-y-1">
              <Label>business_status</Label>
              <Input
                onChange={(e) =>
                  setUpdateForm({ ...updateForm, business_status: e.target.value || undefined })
                }
              />
            </div>

            <div className="space-y-1">
              <Label>confidence_score</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                max="1"
                onChange={(e) =>
                  setUpdateForm({
                    ...updateForm,
                    confidence_score: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
              />
            </div>
            <div className="space-y-1">
              <Label>state (e.g., VERIFIED)</Label>
              <Input
                onChange={(e) => setUpdateForm({ ...updateForm, state: e.target.value || undefined })}
              />
            </div>
            <div className="md:col-span-3 space-y-1">
              <Label>notes</Label>
              <Input
                onChange={(e) => setUpdateForm({ ...updateForm, notes: e.target.value || undefined })}
              />
            </div>
          </div>

          <div className="pt-2">
            <Button variant="secondary" onClick={doUpdate}>
              Updaten
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* RESULT */}
      <Card>
        <CardHeader>
          <CardTitle>Result</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="whitespace-pre-wrap text-sm">{result}</pre>
        </CardContent>
      </Card>
    </div>
  );
}
