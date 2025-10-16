// Frontend/src/components/AdminPanel.tsx
import { useState } from "react";
import axios from "axios";

// Eenvoudig paneel voor create + update.
// Vereist dat VITE_API_BASE_URL is gezet (zie TDA-5).
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000") + "/api/v1";

// Admin key via local storage of env (niet bundelen in code!):
function getAdminKey(): string {
  const v = localStorage.getItem("ADMIN_API_KEY") || "";
  return v;
}

type CreatePayload = {
  name: string;
  address: string;
  lat: number;
  lng: number;
  category: string;
  business_status?: string;
  rating?: number | null;
  user_ratings_total?: number | null;
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
    rating: null,
    user_ratings_total: null,
    notes: "",
    is_probable_not_open_yet: false,
  });

  const [updateId, setUpdateId] = useState<number | "">("");
  const [updateForm, setUpdateForm] = useState<UpdatePayload>({});
  const [result, setResult] = useState<string>("");

  async function doCreate() {
    setResult("");
    try {
      const res = await axios.post(`${API_BASE}/admin/locations`, createForm, {
        headers: { "X-Admin-Key": getAdminKey() },
      });
      setResult(JSON.stringify(res.data, null, 2));
    } catch (e: any) {
      setResult(e?.response?.data?.detail || e.message);
    }
  }

  async function doUpdate() {
    if (!updateId || typeof updateId !== "number") {
      setResult("Vul een geldige ID in voor update.");
      return;
    }
    setResult("");
    try {
      const res = await axios.patch(`${API_BASE}/admin/locations/${updateId}`, updateForm, {
        headers: { "X-Admin-Key": getAdminKey() },
      });
      setResult(JSON.stringify(res.data, null, 2));
    } catch (e: any) {
      setResult(e?.response?.data?.detail || e.message);
    }
  }

  return (
    <div className="p-4 space-y-6">
      <h2 className="text-xl font-bold">Admin Panel (Locations)</h2>

      {/* CREATE */}
      <div className="p-4 border rounded-md">
        <h3 className="font-semibold mb-2">Nieuwe locatie aanmaken (auto VERIFIED)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input className="border p-2" placeholder="Name" value={createForm.name}
                 onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} />
          <input className="border p-2" placeholder="Address" value={createForm.address}
                 onChange={(e) => setCreateForm({ ...createForm, address: e.target.value })} />
          <input className="border p-2" placeholder="Lat" type="number" value={createForm.lat}
                 onChange={(e) => setCreateForm({ ...createForm, lat: parseFloat(e.target.value) })} />
          <input className="border p-2" placeholder="Lng" type="number" value={createForm.lng}
                 onChange={(e) => setCreateForm({ ...createForm, lng: parseFloat(e.target.value) })} />
          <input className="border p-2" placeholder="Category" value={createForm.category}
                 onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })} />
          <input className="border p-2" placeholder="Business Status" value={createForm.business_status || ""}
                 onChange={(e) => setCreateForm({ ...createForm, business_status: e.target.value })} />
          <input className="border p-2" placeholder="Rating" type="number" value={createForm.rating ?? ""}
                 onChange={(e) => setCreateForm({ ...createForm, rating: e.target.value ? parseFloat(e.target.value) : null })} />
          <input className="border p-2" placeholder="User Ratings Total" type="number" value={createForm.user_ratings_total ?? ""}
                 onChange={(e) => setCreateForm({ ...createForm, user_ratings_total: e.target.value ? parseInt(e.target.value) : null })} />
          <input className="border p-2 md:col-span-2" placeholder="Notes" value={createForm.notes || ""}
                 onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={!!createForm.is_probable_not_open_yet}
                   onChange={(e) => setCreateForm({ ...createForm, is_probable_not_open_yet: e.target.checked })} />
            Probable Not Open Yet
          </label>
        </div>
        <button className="mt-3 px-3 py-2 bg-black text-white rounded" onClick={doCreate}>Aanmaken</button>
      </div>

      {/* UPDATE */}
      <div className="p-4 border rounded-md">
        <h3 className="font-semibold mb-2">Bestaande locatie bewerken</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input className="border p-2" placeholder="Location ID" value={updateId}
                 onChange={(e) => setUpdateId(e.target.value ? parseInt(e.target.value) : "")} />
          <input className="border p-2" placeholder="name"
                 onChange={(e) => setUpdateForm({ ...updateForm, name: e.target.value || undefined })} />
          <input className="border p-2" placeholder="address"
                 onChange={(e) => setUpdateForm({ ...updateForm, address: e.target.value || undefined })} />
          <input className="border p-2" placeholder="lat" type="number"
                 onChange={(e) => setUpdateForm({ ...updateForm, lat: e.target.value ? parseFloat(e.target.value) : undefined })} />
          <input className="border p-2" placeholder="lng" type="number"
                 onChange={(e) => setUpdateForm({ ...updateForm, lng: e.target.value ? parseFloat(e.target.value) : undefined })} />
          <input className="border p-2" placeholder="category"
                 onChange={(e) => setUpdateForm({ ...updateForm, category: e.target.value || undefined })} />
          <input className="border p-2" placeholder="business_status"
                 onChange={(e) => setUpdateForm({ ...updateForm, business_status: e.target.value || undefined })} />
          <input className="border p-2" placeholder="rating" type="number"
                 onChange={(e) => setUpdateForm({ ...updateForm, rating: e.target.value ? parseFloat(e.target.value) : undefined })} />
          <input className="border p-2" placeholder="user_ratings_total" type="number"
                 onChange={(e) => setUpdateForm({ ...updateForm, user_ratings_total: e.target.value ? parseInt(e.target.value) : undefined })} />
          <input className="border p-2" placeholder="confidence_score" type="number" step="0.01" min="0" max="1"
                 onChange={(e) => setUpdateForm({ ...updateForm, confidence_score: e.target.value ? parseFloat(e.target.value) : undefined })} />
          <input className="border p-2" placeholder="state (e.g., VERIFIED)"
                 onChange={(e) => setUpdateForm({ ...updateForm, state: e.target.value || undefined })} />
          <input className="border p-2 md:col-span-3" placeholder="notes"
                 onChange={(e) => setUpdateForm({ ...updateForm, notes: e.target.value || undefined })} />
        </div>
        <button className="mt-3 px-3 py-2 bg-black text-white rounded" onClick={doUpdate}>Updaten</button>
      </div>

      {/* RESULT */}
      <div className="p-4 border rounded-md">
        <h3 className="font-semibold mb-2">Result</h3>
        <pre className="whitespace-pre-wrap text-sm">{result}</pre>
      </div>
    </div>
  );
}
