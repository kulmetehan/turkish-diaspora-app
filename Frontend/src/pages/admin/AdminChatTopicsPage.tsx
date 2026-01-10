// Frontend/src/pages/admin/AdminChatTopicsPage.tsx
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  createAdminGeneralTopic,
  deleteAdminChatTopic,
  listAdminChatTopics,
  pinChatTopic,
  unpinChatTopic,
  updateAdminChatTopic,
  type AdminChatTopic,
  type CreateGeneralTopicRequest,
  type UpdateGeneralTopicRequest,
} from "@/lib/apiAdmin";
import { cn } from "@/lib/ui/cn";
import { format } from "date-fns";
import { nl } from "date-fns/locale";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function AdminChatTopicsPage() {
  const [topics, setTopics] = useState<AdminChatTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<AdminChatTopic | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [topicToDelete, setTopicToDelete] = useState<number | null>(null);

  const loadTopics = async () => {
    setLoading(true);
    try {
      const data = await listAdminChatTopics({ limit: 100 });
      setTopics(data);
    } catch (err: any) {
      toast.error("Kon chat topics niet laden", { description: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopics();
  }, []);

  const handleDelete = async (id: number) => {
    setTopicToDelete(id);
    setDeleteConfirmOpen(true);
  };

  const handlePin = async (id: number, currentlyPinned: boolean) => {
    try {
      if (currentlyPinned) {
        await unpinChatTopic(id);
        toast.success("Chat topic losgemaakt");
      } else {
        await pinChatTopic(id);
        toast.success("Chat topic vastgezet");
      }
      await loadTopics();
    } catch (err: any) {
      toast.error("Kon chat topic niet pinnen/unpinnen", { description: err.message });
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Chat Topics Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Beheer Turkchat topics (general topics) en pin/unpin chats
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Icon name="Plus" className="h-4 w-4 mr-2" />
          Nieuw Topic
        </Button>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Laden...
          </CardContent>
        </Card>
      ) : topics.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Geen chat topics gevonden. Maak je eerste topic aan!
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {topics.map((topic) => (
            <Card key={topic.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <CardTitle className="text-lg">{topic.title}</CardTitle>
                      {topic.is_pinned && (
                        <Badge variant="secondary" className="gap-1">
                          <Icon name="Pin" className="h-3 w-3" />
                          Vastgezet
                        </Badge>
                      )}
                    </div>
                    {topic.description && (
                      <p className="text-sm text-muted-foreground mt-1">{topic.description}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant={topic.is_pinned ? "default" : "outline"}
                      size="sm"
                      onClick={() => handlePin(topic.id, topic.is_pinned || false)}
                      title={topic.is_pinned ? "Losmaken" : "Vastzetten"}
                    >
                      <Icon
                        name="Pin"
                        className={cn("h-4 w-4", topic.is_pinned && "fill-current")}
                      />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedTopic(topic);
                        setEditDialogOpen(true);
                      }}
                    >
                      <Icon name="Edit" className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(topic.id)}
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 text-sm">
                  {topic.topic_category && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Categorie:</span>
                      <Badge variant="outline" className="capitalize">
                        {topic.topic_category}
                      </Badge>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Content Type:</span>
                    <span className="font-medium">{topic.content_type}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Berichten:</span>
                    <span className="font-medium">{topic.message_count}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Aangemaakt:</span>
                    <span className="font-medium">
                      {format(new Date(topic.created_at), "PPp", { locale: nl })}
                    </span>
                  </div>
                  {topic.last_message_at && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Laatste bericht:</span>
                      <span className="font-medium">
                        {format(new Date(topic.last_message_at), "PPp", { locale: nl })}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateTopicDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          setCreateDialogOpen(false);
          loadTopics();
        }}
      />

      <EditTopicDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        topic={selectedTopic}
        onSuccess={() => {
          setEditDialogOpen(false);
          setSelectedTopic(null);
          loadTopics();
        }}
      />

      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chat Topic Verwijderen</DialogTitle>
            <DialogDescription>
              Weet je zeker dat je dit chat topic wilt verwijderen? Deze actie kan niet ongedaan worden gemaakt.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              Annuleren
            </Button>
            <Button variant="destructive" onClick={async () => {
              if (!topicToDelete) return;
              try {
                await deleteAdminChatTopic(topicToDelete);
                toast.success("Chat topic verwijderd");
                await loadTopics();
                setDeleteConfirmOpen(false);
                setTopicToDelete(null);
              } catch (err: any) {
                toast.error("Kon chat topic niet verwijderen", { description: err.message });
              }
            }}>
              Verwijderen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreateTopicDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState<CreateGeneralTopicRequest>({
    title: "",
    description: null,
    topic_category: null,
    image_url: null,
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.title.trim()) {
      toast.error("Titel is verplicht");
      return;
    }

    setSubmitting(true);
    try {
      await createAdminGeneralTopic(formData);
      toast.success("Chat topic aangemaakt");
      onSuccess();
      // Reset form
      setFormData({
        title: "",
        description: null,
        topic_category: null,
        image_url: null,
      });
    } catch (err: any) {
      toast.error("Kon chat topic niet aanmaken", { description: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Nieuw Turkchat Topic</DialogTitle>
          <DialogDescription>
            Maak een nieuw general chat topic aan voor Turkchat
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Titel *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="Bijv. Voetbalchat, Vrouwenchat, Algemeen"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Beschrijving (optioneel)</Label>
            <Textarea
              id="description"
              value={formData.description || ""}
              onChange={(e) => setFormData({ ...formData, description: e.target.value || null })}
              placeholder="Korte beschrijving van het topic"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="topic_category">Categorie (optioneel)</Label>
            <Input
              id="topic_category"
              value={formData.topic_category || ""}
              onChange={(e) => setFormData({ ...formData, topic_category: e.target.value || null })}
              placeholder="Bijv. Voetbalchat, Vrouwenchat, Algemeen"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="image_url">Afbeelding URL (optioneel)</Label>
            <Input
              id="image_url"
              type="url"
              value={formData.image_url || ""}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value || null })}
              placeholder="https://example.com/image.jpg"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuleren
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Aanmaken..." : "Aanmaken"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditTopicDialog({
  open,
  onOpenChange,
  topic,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  topic: AdminChatTopic | null;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState<UpdateGeneralTopicRequest>({
    title: "",
    description: null,
    topic_category: null,
    image_url: null,
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (topic) {
      setFormData({
        title: topic.title,
        description: topic.description || null,
        topic_category: topic.topic_category || null,
        image_url: topic.image_url || null,
      });
    }
  }, [topic]);

  if (!topic) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.title?.trim()) {
      toast.error("Titel is verplicht");
      return;
    }

    setSubmitting(true);
    try {
      await updateAdminChatTopic(topic.id, formData);
      toast.success("Chat topic bijgewerkt");
      onSuccess();
    } catch (err: any) {
      toast.error("Kon chat topic niet bijwerken", { description: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Chat Topic Bewerken</DialogTitle>
          <DialogDescription>
            Bewerk het chat topic
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit_title">Titel *</Label>
            <Input
              id="edit_title"
              value={formData.title || ""}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="Bijv. Voetbalchat, Vrouwenchat, Algemeen"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit_description">Beschrijving (optioneel)</Label>
            <Textarea
              id="edit_description"
              value={formData.description || ""}
              onChange={(e) => setFormData({ ...formData, description: e.target.value || null })}
              placeholder="Korte beschrijving van het topic"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit_topic_category">Categorie (optioneel)</Label>
            <Input
              id="edit_topic_category"
              value={formData.topic_category || ""}
              onChange={(e) => setFormData({ ...formData, topic_category: e.target.value || null })}
              placeholder="Bijv. Voetbalchat, Vrouwenchat, Algemeen"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit_image_url">Afbeelding URL (optioneel)</Label>
            <Input
              id="edit_image_url"
              type="url"
              value={formData.image_url || ""}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value || null })}
              placeholder="https://example.com/image.jpg"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuleren
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Opslaan..." : "Opslaan"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

