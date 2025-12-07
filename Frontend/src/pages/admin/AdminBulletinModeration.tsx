// Frontend/src/pages/admin/AdminBulletinModeration.tsx
import { useState, useEffect } from "react";
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
  getBulletinReviewQueue,
  moderateBulletinPost,
  type AdminBulletinPost,
} from "@/lib/apiAdmin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";
import { Skeleton } from "@/components/ui/skeleton";

const categoryLabels: Record<string, string> = {
  personnel_wanted: "Personeel gezocht",
  offer: "Aanbieding",
  free_for_sale: "Gratis/Te koop",
  event: "Evenement",
  services: "Diensten",
  other: "Overig",
};

const moderationStatusLabels: Record<string, string> = {
  pending: "In behandeling",
  approved: "Goedgekeurd",
  rejected: "Afgewezen",
  requires_review: "Review nodig",
  reported: "Gerapporteerd",
};

export default function AdminBulletinModeration() {
  const [posts, setPosts] = useState<AdminBulletinPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [moderatingIds, setModeratingIds] = useState<Set<number>>(new Set());

  const loadPosts = async () => {
    setLoading(true);
    try {
      const data = await getBulletinReviewQueue(statusFilter !== "all" ? statusFilter : undefined);
      setPosts(data);
    } catch (err: any) {
      toast.error("Kon posts niet laden", { description: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPosts();
  }, [statusFilter]);

  const handleModerate = async (postId: number, action: "approve" | "reject") => {
    if (!confirm(`Weet je zeker dat je deze post wilt ${action === "approve" ? "goedkeuren" : "afwijzen"}?`)) {
      return;
    }

    setModeratingIds((prev) => new Set(prev).add(postId));
    try {
      await moderateBulletinPost(postId, action);
      toast.success(`Post ${action === "approve" ? "goedgekeurd" : "afgewezen"}`);
      await loadPosts();
    } catch (err: any) {
      toast.error(`Kon post niet ${action === "approve" ? "goedkeuren" : "afwijzen"}`, {
        description: err.message,
      });
    } finally {
      setModeratingIds((prev) => {
        const next = new Set(prev);
        next.delete(postId);
        return next;
      });
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return format(new Date(dateStr), "d MMM yyyy 'om' HH:mm", { locale: nl });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Bulletin Moderation</h1>
          <p className="text-muted-foreground">Beoordeel advertenties die handmatige review nodig hebben</p>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle statussen</SelectItem>
            <SelectItem value="requires_review">Review nodig</SelectItem>
            <SelectItem value="reported">Gerapporteerd</SelectItem>
            <SelectItem value="pending">In behandeling</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : posts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Geen posts gevonden die review nodig hebben
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Card key={post.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <CardTitle className="text-lg mb-2">{post.title}</CardTitle>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary">
                        {categoryLabels[post.category] || post.category}
                      </Badge>
                      <Badge
                        variant={
                          post.moderation_status === "reported"
                            ? "destructive"
                            : post.moderation_status === "requires_review"
                            ? "default"
                            : "outline"
                        }
                      >
                        {moderationStatusLabels[post.moderation_status] || post.moderation_status}
                      </Badge>
                      {post.city && (
                        <Badge variant="outline">
                          <Icon name="MapPin" className="h-3 w-3 mr-1" />
                          {post.city}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatDate(post.created_at)}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {post.description && (
                  <p className="text-sm text-muted-foreground">{post.description}</p>
                )}

                {post.moderation_result && (
                  <div className="p-3 bg-muted rounded-lg">
                    <p className="text-xs font-semibold mb-1">AI Moderation Result:</p>
                    <p className="text-xs text-muted-foreground">
                      <strong>Beslissing:</strong> {post.moderation_result.decision}
                      <br />
                      <strong>Reden:</strong> {post.moderation_result.reason}
                      {post.moderation_result.details && (
                        <>
                          <br />
                          <strong>Details:</strong> {post.moderation_result.details}
                        </>
                      )}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>
                      <Icon name="Eye" className="h-3 w-3 inline mr-1" />
                      {post.view_count} weergaven
                    </span>
                    <span>
                      <Icon name="Phone" className="h-3 w-3 inline mr-1" />
                      {post.contact_count} contacten
                    </span>
                    <span>Door: {post.creator_type}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleModerate(post.id, "reject")}
                      disabled={moderatingIds.has(post.id)}
                      className="text-destructive"
                    >
                      <Icon name="X" className="h-4 w-4 mr-1" />
                      Afwijzen
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleModerate(post.id, "approve")}
                      disabled={moderatingIds.has(post.id)}
                    >
                      <Icon name="Check" className="h-4 w-4 mr-1" />
                      Goedkeuren
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

