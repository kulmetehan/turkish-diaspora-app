import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Icon } from "@/components/Icon";
import { 
  getMySocialAccounts, 
  createSocialAccount, 
  deleteSocialAccount,
  type SocialAccount,
  type SocialAccountCreate 
} from "@/lib/api";
import { toast } from "sonner";
import { useTranslation } from "@/hooks/useTranslation";
import { X, Plus } from "lucide-react";

const PLATFORMS = [
  { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'snapchat', label: 'Snapchat' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'tiktok', label: 'TikTok' },
];

const SOCIAL_ICONS: Record<string, string> = {
  facebook: "Facebook",
  instagram: "Instagram",
  snapchat: "MessageCircle",
  youtube: "Youtube",
  whatsapp: "MessageCircle",
  tiktok: "Music", // TikTok icon doesn't exist in lucide-react, using Music as fallback
};

export function SocialAccountsSection({ className }: { className?: string }) {
  const { t } = useTranslation();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [newAccount, setNewAccount] = useState<SocialAccountCreate>({
    platform: '',
    username: '',
    url: '',
    display_order: 0,
  });
  
  useEffect(() => {
    loadAccounts();
  }, []);
  
  const loadAccounts = async () => {
    try {
      const data = await getMySocialAccounts();
      setAccounts(data);
    } catch (error) {
      console.error("Failed to load social accounts:", error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleAdd = async () => {
    if (!newAccount.platform || !newAccount.username || !newAccount.url) {
      toast.error("Vul alle velden in");
      return;
    }
    
    // Basic URL validation
    if (!newAccount.url.startsWith('http://') && !newAccount.url.startsWith('https://')) {
      toast.error("URL moet beginnen met http:// of https://");
      return;
    }
    
    try {
      const created = await createSocialAccount({
        ...newAccount,
        display_order: accounts.length,
      });
      setAccounts([...accounts, created]);
      setNewAccount({ platform: '', username: '', url: '', display_order: 0 });
      setIsAdding(false);
      toast.success("Social account toegevoegd");
    } catch (error: any) {
      toast.error(error.message || "Kon account niet toevoegen");
    }
  };
  
  const handleDelete = async (id: number) => {
    if (!confirm("Weet je zeker dat je dit account wilt verwijderen?")) {
      return;
    }
    
    try {
      await deleteSocialAccount(id);
      setAccounts(accounts.filter(a => a.id !== id));
      toast.success("Account verwijderd");
    } catch (error: any) {
      toast.error(error.message || "Kon account niet verwijderen");
    }
  };
  
  return (
    <Card className={className}>
      <div className="p-6 space-y-4">
        <div className="space-y-1">
          <h3 className="text-lg font-gilroy font-medium text-foreground">
            Sociale Accounts
          </h3>
          <p className="text-sm text-muted-foreground">
            Voeg je sociale media profielen toe zodat anderen je kunnen vinden
          </p>
        </div>
        
        {loading ? (
          <div className="text-sm text-muted-foreground">Laden...</div>
        ) : (
          <>
            {/* Existing accounts */}
            {accounts.length > 0 && (
              <div className="space-y-2">
                {accounts.map((account) => (
                  <div
                    key={account.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted"
                  >
                    <div className="flex items-center gap-2">
                      <Icon name={SOCIAL_ICONS[account.platform] || "Globe"} className="h-4 w-4" />
                      <span className="text-sm font-medium">{account.username}</span>
                      <span className="text-xs text-muted-foreground">({account.platform})</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(account.id)}
                      className="h-8 w-8 p-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            
            {/* Add new account form */}
            {isAdding ? (
              <div className="space-y-3 p-3 border border-border rounded-lg">
                <Select
                  value={newAccount.platform}
                  onValueChange={(value) => setNewAccount({ ...newAccount, platform: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecteer platform" />
                  </SelectTrigger>
                  <SelectContent className="z-[100]">
                    {PLATFORMS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Input
                  placeholder="Gebruikersnaam of @handle"
                  value={newAccount.username}
                  onChange={(e) => setNewAccount({ ...newAccount, username: e.target.value })}
                />
                
                <Input
                  placeholder="https://..."
                  value={newAccount.url}
                  onChange={(e) => setNewAccount({ ...newAccount, url: e.target.value })}
                />
                
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleAdd}>
                    Opslaan
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setIsAdding(false);
                      setNewAccount({ platform: '', username: '', url: '', display_order: 0 });
                    }}
                  >
                    Annuleren
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAdding(true)}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Account toevoegen
              </Button>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

