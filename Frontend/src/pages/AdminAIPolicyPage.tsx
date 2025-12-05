import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getAIConfig, updateAIConfig, type AIConfig, type AIConfigUpdate } from "@/lib/api";
import { toast } from "sonner";

export default function AdminAIPolicyPage() {
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<AIConfigUpdate>({});

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    try {
      setLoading(true);
      const data = await getAIConfig();
      setConfig(data);
      setFormData({});
    } catch (error: any) {
      toast.error(`Failed to load AI config: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    try {
      setSaving(true);
      const updated = await updateAIConfig(formData);
      setConfig(updated);
      setFormData({});
      toast.success("AI policy configuration updated successfully");
    } catch (error: any) {
      toast.error(`Failed to update AI config: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  function updateField(field: keyof AIConfigUpdate, value: number) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  function getValue(field: keyof AIConfig): number {
    return formData[field as keyof AIConfigUpdate] ?? config?.[field] ?? 0;
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-sm text-muted-foreground">Loading AI policy configuration...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-6">
        <div className="text-sm text-muted-foreground">Failed to load configuration</div>
      </div>
    );
  }

  const hasChanges = Object.keys(formData).length > 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">AI Policy Configuration</h1>
        <p className="text-sm text-muted-foreground">
          Manage confidence thresholds and freshness policies for AI workers. Changes take effect on the next worker run.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Confidence Thresholds */}
        <Card>
          <CardHeader>
            <CardTitle>Confidence Thresholds</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">Minimum confidence scores (0.0 - 1.0) for worker decisions</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="classify_min_conf">
                Classify Bot Minimum Confidence
                <span className="text-xs text-muted-foreground block mt-1">
                  Minimum confidence for classify_bot to apply classification. Lower = more lenient.
                </span>
              </Label>
              <Input
                id="classify_min_conf"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={getValue("classify_min_conf")}
                onChange={(e) => updateField("classify_min_conf", parseFloat(e.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="verify_min_conf">
                Verify Locations Minimum Confidence
                <span className="text-xs text-muted-foreground block mt-1">
                  Minimum confidence for verify_locations bot to promote to VERIFIED. Lower = more promotions.
                </span>
              </Label>
              <Input
                id="verify_min_conf"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={getValue("verify_min_conf")}
                onChange={(e) => updateField("verify_min_conf", parseFloat(e.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="task_verifier_min_conf">
                Task Verifier Minimum Confidence
                <span className="text-xs text-muted-foreground block mt-1">
                  Minimum confidence for task_verifier bot. Lower = more lenient.
                </span>
              </Label>
              <Input
                id="task_verifier_min_conf"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={getValue("task_verifier_min_conf")}
                onChange={(e) => updateField("task_verifier_min_conf", parseFloat(e.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="auto_promote_conf">
                Auto-Promotion Threshold
                <span className="text-xs text-muted-foreground block mt-1">
                  Auto-promotion threshold for task_verifier (high confidence + Turkish cues). Lower = more auto-promotions.
                </span>
              </Label>
              <Input
                id="auto_promote_conf"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={getValue("auto_promote_conf")}
                onChange={(e) => updateField("auto_promote_conf", parseFloat(e.target.value) || 0)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Freshness Policy Intervals */}
        <Card>
          <CardHeader>
            <CardTitle>Freshness Policy Intervals</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">Days between verification checks based on confidence and review count</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="monitor_low_conf_days">
                Low Confidence Days (Fast)
                <span className="text-xs text-muted-foreground block mt-1">
                  Check interval for locations with confidence &lt; 0.60. Lower = check more frequently.
                </span>
              </Label>
              <Input
                id="monitor_low_conf_days"
                type="number"
                min="1"
                step="1"
                value={getValue("monitor_low_conf_days")}
                onChange={(e) => updateField("monitor_low_conf_days", parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="monitor_medium_conf_days">
                Medium Confidence Days (Slow)
                <span className="text-xs text-muted-foreground block mt-1">
                  Check interval for locations with confidence 0.60-0.80. Lower = check more frequently.
                </span>
              </Label>
              <Input
                id="monitor_medium_conf_days"
                type="number"
                min="1"
                step="1"
                value={getValue("monitor_medium_conf_days")}
                onChange={(e) => updateField("monitor_medium_conf_days", parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="monitor_high_conf_days">
                High Confidence Days
                <span className="text-xs text-muted-foreground block mt-1">
                  Check interval for locations with confidence &gt;= 0.80. Lower = check more frequently.
                </span>
              </Label>
              <Input
                id="monitor_high_conf_days"
                type="number"
                min="1"
                step="1"
                value={getValue("monitor_high_conf_days")}
                onChange={(e) => updateField("monitor_high_conf_days", parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="monitor_verified_few_reviews_days">
                Verified: Few Reviews (&lt; 10)
                <span className="text-xs text-muted-foreground block mt-1">
                  Check interval for VERIFIED locations with &lt; 10 reviews. Lower = check more frequently.
                </span>
              </Label>
              <Input
                id="monitor_verified_few_reviews_days"
                type="number"
                min="1"
                step="1"
                value={getValue("monitor_verified_few_reviews_days")}
                onChange={(e) => updateField("monitor_verified_few_reviews_days", parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="monitor_verified_medium_reviews_days">
                Verified: Medium Reviews (10-99)
                <span className="text-xs text-muted-foreground block mt-1">
                  Check interval for VERIFIED locations with 10-99 reviews. Lower = check more frequently.
                </span>
              </Label>
              <Input
                id="monitor_verified_medium_reviews_days"
                type="number"
                min="1"
                step="1"
                value={getValue("monitor_verified_medium_reviews_days")}
                onChange={(e) => updateField("monitor_verified_medium_reviews_days", parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="monitor_verified_many_reviews_days">
                Verified: Many Reviews (&gt;= 100)
                <span className="text-xs text-muted-foreground block mt-1">
                  Check interval for VERIFIED locations with &gt;= 100 reviews. Lower = check more frequently.
                </span>
              </Label>
              <Input
                id="monitor_verified_many_reviews_days"
                type="number"
                min="1"
                step="1"
                value={getValue("monitor_verified_many_reviews_days")}
                onChange={(e) => updateField("monitor_verified_many_reviews_days", parseInt(e.target.value) || 1)}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {config.updated_by && (
            <span>
              Last updated by {config.updated_by} on {new Date(config.updated_at).toLocaleString()}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadConfig} disabled={loading || saving}>
            Reset
          </Button>
          <Button onClick={handleSave} disabled={!hasChanges || saving || loading}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}

