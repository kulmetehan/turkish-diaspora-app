import AuthenticatedClaimsList from "@/components/admin/AuthenticatedClaimsList";

export default function AdminAuthenticatedClaimsPage() {
  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Authenticated Claims</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Review and manage location claim requests from authenticated users
        </p>
      </div>
      <AuthenticatedClaimsList />
    </div>
  );
}

