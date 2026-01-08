// Frontend/src/components/polls/CreatePollDialog.tsx
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { createPoll, type PollCreateRequest } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { useState } from "react";
import { toast } from "sonner";

interface CreatePollDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function CreatePollDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreatePollDialogProps) {
  const [formData, setFormData] = useState<PollCreateRequest>({
    title: "",
    question: "",
    poll_type: "single_choice",
    options: [
      { option_text: "", display_order: 0 },
      { option_text: "", display_order: 1 },
    ],
    targeting_city_key: null,
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate
    if (!formData.title.trim() || !formData.question.trim()) {
      toast.error("Titel en vraag zijn verplicht");
      return;
    }

    if (formData.options.length < 2) {
      toast.error("Minimaal 2 opties zijn vereist");
      return;
    }

    if (formData.options.some((opt) => !opt.option_text.trim())) {
      toast.error("Alle opties moeten tekst bevatten");
      return;
    }

    setSubmitting(true);
    try {
      await createPoll(formData);
      toast.success("Poll succesvol aangemaakt");
      onSuccess();
      // Reset form
      setFormData({
        title: "",
        question: "",
        poll_type: "single_choice",
        options: [
          { option_text: "", display_order: 0 },
          { option_text: "", display_order: 1 },
        ],
        targeting_city_key: null,
      });
      onOpenChange(false);
    } catch (err: any) {
      toast.error("Kon poll niet aanmaken", {
        description: err.message || "Er is een fout opgetreden",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const addOption = () => {
    if (formData.options.length >= 5) {
      toast.error("Maximaal 5 opties toegestaan");
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
      toast.error("Minimaal 2 opties zijn vereist");
      return;
    }
    setFormData({
      ...formData,
      options: formData.options
        .filter((_, i) => i !== index)
        .map((opt, i) => ({
          ...opt,
          display_order: i,
        })),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nieuwe poll plaatsen</DialogTitle>
          <DialogDescription>
            Maak een poll aan die anderen kunnen beantwoorden
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Titel *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) =>
                setFormData({ ...formData, title: e.target.value })
              }
              placeholder="Bijv: Wat is je favoriete Turkse gerecht?"
              required
              maxLength={100}
            />
          </div>

          {/* Question */}
          <div className="space-y-2">
            <Label htmlFor="question">Vraag *</Label>
            <Textarea
              id="question"
              value={formData.question}
              onChange={(e) =>
                setFormData({ ...formData, question: e.target.value })
              }
              placeholder="Stel je vraag hier..."
              required
              rows={3}
              maxLength={500}
            />
          </div>

          {/* Options */}
          <div className="space-y-2">
            <Label>Opties * (minimaal 2, maximaal 5)</Label>
            <div className="space-y-2">
              {formData.options.map((option, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    value={option.option_text}
                    onChange={(e) => {
                      const newOptions = [...formData.options];
                      newOptions[index] = {
                        ...newOptions[index],
                        option_text: e.target.value,
                      };
                      setFormData({ ...formData, options: newOptions });
                    }}
                    placeholder={`Optie ${index + 1}`}
                    required
                    maxLength={200}
                    className="flex-1"
                  />
                  {formData.options.length > 2 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeOption(index)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Icon name="Trash2" className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            {formData.options.length < 5 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addOption}
                className="w-full"
              >
                <Icon name="Plus" className="h-4 w-4 mr-2" />
                Optie toevoegen
              </Button>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              Annuleren
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Aanmaken..." : "Poll plaatsen"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}








