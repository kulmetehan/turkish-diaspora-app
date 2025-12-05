import AdminLocationsTable from "@/components/admin/AdminLocationsTable";

export default function LocationsPage() {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Locations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage and review all business locations
        </p>
      </div>
      <AdminLocationsTable />
    </div>
  );
}






