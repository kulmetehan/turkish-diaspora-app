import OutreachContactsList from "@/components/admin/OutreachContactsList";

export default function AdminOutreachContactsPage() {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Outreach Contacts</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage contact information for locations. Contacts can be discovered automatically or added manually.
        </p>
      </div>
      <OutreachContactsList />
    </div>
  );
}

