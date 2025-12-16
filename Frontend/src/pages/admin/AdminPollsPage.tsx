// Frontend/src/pages/admin/AdminPollsPage.tsx
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Icon } from "@/components/Icon";
import {
  listAdminPolls,
  createAdminPoll,
  updateAdminPoll,
  deleteAdminPoll,
  type AdminPoll,
  type AdminPollCreateRequest,
} from "@/lib/apiAdmin";
import { format } from "date-fns";
import { nl } from "date-fns/locale";

export default function AdminPollsPage() {
  const [polls, setPolls] = useState<AdminPoll[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedPoll, setSelectedPoll] = useState<AdminPoll | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [pollToDelete, setPollToDelete] = useState<number | null>(null);

  const loadPolls = async () => {
    setLoading(true);
    try {
      const data = await listAdminPolls({ limit: 100 });
      setPolls(data);
    } catch (err: any) {
      toast.error("Failed to load polls", { description: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolls();
  }, []);

  const handleDelete = async (id: number) => {
    setPollToDelete(id);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!pollToDelete) return;
    try {
      await deleteAdminPoll(pollToDelete);
      toast.success("Poll deleted");
      await loadPolls();
      setDeleteConfirmOpen(false);
      setPollToDelete(null);
    } catch (err: any) {
      toast.error("Failed to delete poll", { description: err.message });
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Polls Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage daily polls for users
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Icon name="Plus" className="h-4 w-4 mr-2" />
          New Poll
        </Button>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Loading polls...
          </CardContent>
        </Card>
      ) : polls.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            No polls yet. Create your first poll!
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {polls.map((poll) => (
            <Card key={poll.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{poll.title}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">{poll.question}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedPoll(poll);
                        setEditDialogOpen(true);
                      }}
                    >
                      <Icon name="Edit" className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(poll.id)}
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Type:</span>
                    <span className="font-medium">{poll.poll_type}</span>
                  </div>
                  {poll.targeting_city_key && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">City:</span>
                      <span className="font-medium">{poll.targeting_city_key}</span>
                    </div>
                  )}
                  {poll.is_sponsored && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Sponsored:</span>
                      <span className="font-medium text-primary">Yes</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Options:</span>
                    <span className="font-medium">{poll.options.length}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Created:</span>
                    <span className="font-medium">
                      {format(new Date(poll.created_at), "PPp", { locale: nl })}
                    </span>
                  </div>
                  <div className="mt-2">
                    <p className="text-xs text-muted-foreground mb-1">Options:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {poll.options.map((opt) => (
                        <li key={opt.id} className="text-sm">
                          {opt.option_text}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreatePollDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          setCreateDialogOpen(false);
          loadPolls();
        }}
      />

      <EditPollDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        poll={selectedPoll}
        onSuccess={() => {
          setEditDialogOpen(false);
          setSelectedPoll(null);
          loadPolls();
        }}
      />

      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Poll</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this poll? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreatePollDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState<AdminPollCreateRequest>({
    title: "",
    question: "",
    poll_type: "single_choice",
    options: [{ option_text: "", display_order: 0 }, { option_text: "", display_order: 1 }],
    is_sponsored: false,
    targeting_city_key: null,
    starts_at: null,
    ends_at: null,
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate
    if (!formData.title.trim() || !formData.question.trim()) {
      toast.error("Title and question are required");
      return;
    }

    if (formData.options.length < 2) {
      toast.error("At least 2 options are required");
      return;
    }

    if (formData.options.some(opt => !opt.option_text.trim())) {
      toast.error("All options must have text");
      return;
    }

    setSubmitting(true);
    try {
      await createAdminPoll(formData);
      toast.success("Poll created successfully");
      onSuccess();
      // Reset form
      setFormData({
        title: "",
        question: "",
        poll_type: "single_choice",
        options: [{ option_text: "", display_order: 0 }, { option_text: "", display_order: 1 }],
        is_sponsored: false,
        targeting_city_key: null,
        starts_at: null,
        ends_at: null,
      });
    } catch (err: any) {
      toast.error("Failed to create poll", { description: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const addOption = () => {
    if (formData.options.length >= 5) {
      toast.error("Maximum 5 options allowed");
      return;
    }
    setFormData({
      ...formData,
      options: [
        ...formData.options,
        { option_text: "", display_order: formData.options.length },
      ],
    });
  };

  const removeOption = (index: number) => {
    if (formData.options.length <= 2) {
      toast.error("At least 2 options are required");
      return;
    }
    setFormData({
      ...formData,
      options: formData.options.filter((_, i) => i !== index).map((opt, i) => ({
        ...opt,
        display_order: i,
      })),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Poll</DialogTitle>
          <DialogDescription>
            Create a poll for users to respond to
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="Poll title"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="question">Question *</Label>
            <Textarea
              id="question"
              value={formData.question}
              onChange={(e) => setFormData({ ...formData, question: e.target.value })}
              required
              placeholder="Poll question"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="poll_type">Poll Type *</Label>
            <Select
              value={formData.poll_type}
              onValueChange={(value: "single_choice" | "multi_choice") =>
                setFormData({ ...formData, poll_type: value })
              }
            >
              <SelectTrigger id="poll_type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="single_choice">Single Choice</SelectItem>
                <SelectItem value="multi_choice">Multi Choice</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Options * (2-5)</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addOption}
                disabled={formData.options.length >= 5}
              >
                <Icon name="Plus" className="h-4 w-4 mr-1" />
                Add Option
              </Button>
            </div>
            {formData.options.map((opt, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={opt.option_text}
                  onChange={(e) => {
                    const newOptions = [...formData.options];
                    newOptions[index].option_text = e.target.value;
                    setFormData({ ...formData, options: newOptions });
                  }}
                  placeholder={`Option ${index + 1}`}
                  required
                />
                {formData.options.length > 2 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => removeOption(index)}
                  >
                    <Icon name="X" className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Label htmlFor="targeting_city_key">Targeting City (optional)</Label>
            <Input
              id="targeting_city_key"
              value={formData.targeting_city_key || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  targeting_city_key: e.target.value || null,
                })
              }
              placeholder="e.g., rotterdam, amsterdam"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="is_sponsored"
              checked={formData.is_sponsored}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, is_sponsored: Boolean(checked) })
              }
            />
            <Label htmlFor="is_sponsored">Sponsored Poll</Label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="starts_at">Start Date (optional)</Label>
              <Input
                id="starts_at"
                type="datetime-local"
                value={
                  formData.starts_at
                    ? format(new Date(formData.starts_at), "yyyy-MM-dd'T'HH:mm")
                    : ""
                }
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    starts_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                  })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ends_at">End Date (optional)</Label>
              <Input
                id="ends_at"
                type="datetime-local"
                value={
                  formData.ends_at
                    ? format(new Date(formData.ends_at), "yyyy-MM-dd'T'HH:mm")
                    : ""
                }
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    ends_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                  })
                }
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Poll"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditPollDialog({
  open,
  onOpenChange,
  poll,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  poll: AdminPoll | null;
  onSuccess: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);

  if (!poll) return null;

  // Edit dialog is simpler - just allow updating basic fields
  // Option editing would require more complex UI
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Poll</DialogTitle>
          <DialogDescription>
            Edit poll details (option editing coming soon)
          </DialogDescription>
        </DialogHeader>
        <div className="text-sm text-muted-foreground">
          Full edit functionality including options will be available in a future update.
          For now, you can delete and recreate the poll if needed.
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

















