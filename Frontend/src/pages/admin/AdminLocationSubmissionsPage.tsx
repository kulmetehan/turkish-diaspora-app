import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import {
  listLocationSubmissions,
  type LocationSubmissionResponse,
} from "@/lib/apiAdmin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";

export default function AdminLocationSubmissionsPage() {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState<LocationSubmissionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      const data = await listLocationSubmissions({
        status: statusFilter !== "all" ? statusFilter : undefined,
        limit: 200,
      });
      setSubmissions(data);
    } catch (err: any) {
      toast.error("Kon inzendingen niet laden", { description: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubmissions();
  }, [statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">In behandeling</Badge>;
      case "approved":
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">Goedgekeurd</Badge>;
      case "rejected":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-300">Afgewezen</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Locatie Inzendingen</h1>
        <div className="flex items-center gap-4">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter op status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle statussen</SelectItem>
              <SelectItem value="pending">In behandeling</SelectItem>
              <SelectItem value="approved">Goedgekeurd</SelectItem>
              <SelectItem value="rejected">Afgewezen</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Laden...</p>
        </div>
      ) : submissions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Geen inzendingen gevonden.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {submissions.map((submission) => (
            <Card
              key={submission.id}
              className="cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => navigate(`/admin/location-submissions/${submission.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{submission.name}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {submission.address || `${submission.lat.toFixed(6)}, ${submission.lng.toFixed(6)}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(submission.status)}
                    {submission.is_owner && (
                      <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-300">
                        Eigenaar
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-4">
                    <span>Categorie: <strong>{submission.category}</strong></span>
                    {submission.created_location_id && (
                      <span className="text-green-600">
                        Locatie ID: {submission.created_location_id}
                      </span>
                    )}
                  </div>
                  <span>
                    {format(new Date(submission.submitted_at), "d MMM yyyy 'om' HH:mm", { locale: nl })}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}







