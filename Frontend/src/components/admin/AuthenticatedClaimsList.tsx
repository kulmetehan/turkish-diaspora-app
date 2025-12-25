import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import {
  listAuthenticatedClaims,
  type AuthenticatedClaimResponse,
} from "@/lib/apiAdmin";
import { toast } from "sonner";

export default function AuthenticatedClaimsList() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState<AuthenticatedClaimResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"pending" | "approved" | "rejected" | "all">("all");

  const loadClaims = async () => {
    setLoading(true);
    try {
      const params: { status?: "pending" | "approved" | "rejected"; limit?: number; offset?: number } = {
        limit: 100,
        offset: 0,
      };
      if (statusFilter !== "all") {
        params.status = statusFilter;
      }
      const data = await listAuthenticatedClaims(params);
      setClaims(data);
    } catch (error: any) {
      toast.error(`Failed to load claims: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClaims();
  }, [statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">Pending</Badge>;
      case "approved":
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Approved</Badge>;
      case "rejected":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Rejected</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("nl-NL", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Status:</label>
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button variant="outline" size="sm" onClick={loadClaims}>
              <Icon name="RefreshCw" sizeRem={1} className="mr-2" />
              Refresh
            </Button>
          </div>

          {/* Claims List */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-muted-foreground">Loading claims...</div>
            </div>
          ) : claims.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-muted-foreground">No claims found</div>
            </div>
          ) : (
            <div className="space-y-2">
              {claims.map((claim) => (
                <Card
                  key={claim.id}
                  className="cursor-pointer hover:bg-accent transition-colors"
                  onClick={() => navigate(`/admin/authenticated-claims/${claim.id}`)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-3">
                          <h3 className="font-semibold">{claim.location_name || `Location ${claim.location_id}`}</h3>
                          {getStatusBadge(claim.status)}
                        </div>
                        <div className="text-sm text-muted-foreground space-y-1">
                          <div>
                            <strong>User:</strong> {claim.user_name || claim.user_email || "Unknown"}
                          </div>
                          <div>
                            <strong>Submitted:</strong> {formatDate(claim.submitted_at)}
                          </div>
                          {claim.google_business_link && (
                            <div>
                              <strong>Google Business:</strong>{" "}
                              <a
                                href={claim.google_business_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline"
                                onClick={(e) => e.stopPropagation()}
                              >
                                View Link
                              </a>
                            </div>
                          )}
                          {claim.logo_url && (
                            <div>
                              <strong>Logo:</strong> Uploaded
                            </div>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/admin/authenticated-claims/${claim.id}`);
                        }}
                      >
                        <Icon name="ChevronRight" sizeRem={1} />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

