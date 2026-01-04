import { Icon } from "@/components/Icon";
import { type SocialAccount } from "@/lib/api";

const SOCIAL_ICONS: Record<string, string> = {
  facebook: "Facebook",
  instagram: "Instagram",
  snapchat: "MessageCircle",
  youtube: "Youtube",
  whatsapp: "MessageCircle",
  tiktok: "Music", // TikTok icon doesn't exist in lucide-react, using Music as fallback
};

export function UserSocialLinks({ accounts }: { accounts: SocialAccount[] }) {
  // Debug logging in development
  if (process.env.NODE_ENV === 'development') {
    console.log('[UserSocialLinks] Accounts:', accounts);
    accounts.forEach(account => {
      console.log(`[UserSocialLinks] Platform: ${account.platform}, Icon: ${SOCIAL_ICONS[account.platform] || "Globe"}`);
    });
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {accounts
        .sort((a, b) => a.display_order - b.display_order)
        .map((account) => {
          const iconName = SOCIAL_ICONS[account.platform] || "Globe";
          return (
            <a
              key={account.id}
              href={account.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
              title={account.username}
            >
              <Icon name={iconName as any} className="h-5 w-5" />
            </a>
          );
        })}
    </div>
  );
}

