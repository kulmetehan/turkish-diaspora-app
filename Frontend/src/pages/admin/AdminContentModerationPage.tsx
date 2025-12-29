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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import {
  listAdminCheckIns,
  listAdminNotes,
  listAdminPolls,
  listAdminSharedLinks,
  deleteAdminCheckIn,
  deleteAdminNote,
  deleteAdminPoll,
  deleteAdminSharedLink,
  type AdminCheckIn,
  type AdminNote,
  type AdminPoll,
  type AdminSharedLink,
} from "@/lib/apiAdmin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";

type ContentType = "check_in" | "note" | "poll" | "prikbord_post";

export default function AdminContentModerationPage() {
  const [contentType, setContentType] = useState<ContentType>("check_in");
  const [loading, setLoading] = useState(true);
  const [checkIns, setCheckIns] = useState<AdminCheckIn[]>([]);
  const [notes, setNotes] = useState<AdminNote[]>([]);
  const [polls, setPolls] = useState<AdminPoll[]>([]);
  const [sharedLinks, setSharedLinks] = useState<AdminSharedLink[]>([]);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{ type: ContentType; id: number } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const loadContent = async () => {
    setLoading(true);
    try {
      if (contentType === "check_in") {
        const data = await listAdminCheckIns({ limit: 100 });
        setCheckIns(data);
      } else if (contentType === "note") {
        const data = await listAdminNotes({ limit: 100 });
        setNotes(data);
      } else if (contentType === "poll") {
        const data = await listAdminPolls({ limit: 100 });
        setPolls(data);
      } else if (contentType === "prikbord_post") {
        const data = await listAdminSharedLinks({ limit: 100 });
        setSharedLinks(data);
      }
    } catch (err: any) {
      toast.error("Kon content niet laden", { description: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContent();
  }, [contentType]);

  const handleDelete = (type: ContentType, id: number) => {
    setItemToDelete({ type, id });
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!itemToDelete) return;
    setDeleting(true);
    try {
      if (itemToDelete.type === "check_in") {
        await deleteAdminCheckIn(itemToDelete.id);
      } else if (itemToDelete.type === "note") {
        await deleteAdminNote(itemToDelete.id);
      } else if (itemToDelete.type === "poll") {
        await deleteAdminPoll(itemToDelete.id);
      } else if (itemToDelete.type === "prikbord_post") {
        await deleteAdminSharedLink(itemToDelete.id);
      }
      toast.success("Content verwijderd");
      await loadContent();
      setDeleteConfirmOpen(false);
      setItemToDelete(null);
    } catch (err: any) {
      toast.error("Kon content niet verwijderen", { description: err.message });
    } finally {
      setDeleting(false);
    }
  };

  const filterContent = <T extends { user_name?: string | null; user_email?: string | null }>(
    items: T[]
  ): T[] => {
    if (!searchQuery.trim()) return items;
    const query = searchQuery.toLowerCase();
    return items.filter(
      (item) =>
        item.user_name?.toLowerCase().includes(query) ||
        item.user_email?.toLowerCase().includes(query)
    );
  };

  const getTypeLabel = (type: ContentType): string => {
    const labels: Record<ContentType, string> = {
      check_in: "Check-ins",
      note: "Notities",
      poll: "Polls",
      prikbord_post: "Prikbord Posts",
    };
    return labels[type];
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Content Moderatie</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Beheer en verwijder gebruikerscontent
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Select value={contentType} onValueChange={(v) => setContentType(v as ContentType)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="check_in">Check-ins</SelectItem>
            <SelectItem value="note">Notities</SelectItem>
            <SelectItem value="poll">Polls</SelectItem>
            <SelectItem value="prikbord_post">Prikbord Posts</SelectItem>
          </SelectContent>
        </Select>

        <Input
          placeholder="Zoek op gebruiker naam of email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Laden...
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {contentType === "check_in" &&
            filterContent(checkIns).map((checkIn) => (
              <Card key={checkIn.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">Check-in</Badge>
                        <span className="text-sm font-medium">
                          {checkIn.location_name || `Location ${checkIn.location_id}`}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Gebruiker: {checkIn.user_name || checkIn.user_email || "Onbekend"}
                      </p>
                      {checkIn.created_at && (
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(checkIn.created_at), "dd-MM-yyyy HH:mm", { locale: nl })}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete("check_in", checkIn.id)}
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}

          {contentType === "note" &&
            filterContent(notes).map((note) => (
              <Card key={note.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">Notitie</Badge>
                        <span className="text-sm font-medium">
                          {note.location_name || `Location ${note.location_id}`}
                        </span>
                      </div>
                      {note.content && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {note.content}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        Gebruiker: {note.user_name || note.user_email || "Onbekend"}
                      </p>
                      {note.created_at && (
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(note.created_at), "dd-MM-yyyy HH:mm", { locale: nl })}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete("note", note.id)}
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}

          {contentType === "poll" &&
            filterContent(polls as any[]).map((poll) => (
              <Card key={poll.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">Poll</Badge>
                        <span className="text-sm font-medium">{poll.title}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{poll.question}</p>
                      {poll.created_at && (
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(poll.created_at), "dd-MM-yyyy HH:mm", { locale: nl })}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete("poll", poll.id)}
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}

          {contentType === "prikbord_post" &&
            filterContent(sharedLinks as any[]).map((link) => (
              <Card key={link.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">Prikbord</Badge>
                        <span className="text-sm font-medium">{link.title || link.url}</span>
                      </div>
                      {link.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {link.description}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        Gebruiker: {link.user_name || link.user_email || "Onbekend"}
                      </p>
                      {link.created_at && (
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(link.created_at), "dd-MM-yyyy HH:mm", { locale: nl })}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete("prikbord_post", link.id)}
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}

          {((contentType === "check_in" && filterContent(checkIns).length === 0) ||
            (contentType === "note" && filterContent(notes).length === 0) ||
            (contentType === "poll" && filterContent(polls as any[]).length === 0) ||
            (contentType === "prikbord_post" && filterContent(sharedLinks as any[]).length === 0)) && (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                Geen {getTypeLabel(contentType).toLowerCase()} gevonden
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Content verwijderen</DialogTitle>
            <DialogDescription>
              Weet je zeker dat je dit item wilt verwijderen? Deze actie kan niet ongedaan worden
              gemaakt.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              Annuleren
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting ? "Verwijderen..." : "Verwijderen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


