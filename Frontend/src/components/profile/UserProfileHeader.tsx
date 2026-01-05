import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import { type UserProfileDetail } from "@/lib/api";
import { roleDisplayName } from "@/lib/roleDisplay";
import { formatCityLabel } from "@/components/events/eventFormatters";

function getInitials(name: string | null | undefined): string {
  if (!name) return "??";
  const trimmed = name.trim();
  if (!trimmed) return "??";
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return trimmed.substring(0, 2).toUpperCase();
}

function formatLastSeen(lastSeenAt: string | null | undefined): string {
  if (!lastSeenAt) return "Nog niet actief";
  
  const date = new Date(lastSeenAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMinutes < 1) return "Net actief";
  if (diffMinutes < 60) return `${diffMinutes} minuten geleden`;
  if (diffHours < 24) return `${diffHours} uur geleden`;
  if (diffDays < 7) return `${diffDays} dagen geleden`;
  return date.toLocaleDateString('nl-NL', { day: 'numeric', month: 'short' });
}

export function UserProfileHeader({ profile }: { profile: UserProfileDetail }) {
  const displayName = profile.display_name || "Anonieme gebruiker";
  const initials = useMemo(() => getInitials(profile.display_name), [profile.display_name]);
  const lastSeenLabel = useMemo(() => formatLastSeen(profile.last_seen_at), [profile.last_seen_at]);
  
  return (
    <div className="flex flex-col items-center gap-3 pb-4 border-b border-border">
      {/* Avatar */}
      {profile.avatar_url ? (
        <img
          src={profile.avatar_url}
          alt={displayName}
          className="w-20 h-20 rounded-full object-cover border-2 border-primary"
        />
      ) : (
        <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-2xl border-2 border-primary">
          {initials}
        </div>
      )}
      
      {/* Name */}
      <div className="text-center">
        <h2 className="text-xl font-gilroy font-semibold text-foreground">{displayName}</h2>
        
        {/* Badges */}
        <div className="flex items-center justify-center gap-2 mt-2 flex-wrap">
          {profile.city_key && (
            <Badge variant="secondary" className="text-xs">
              <Icon name="MapPin" className="h-3 w-3 mr-1" />
              {formatCityLabel(profile.city_key)}
            </Badge>
          )}
          {profile.primary_role && (
            <Badge variant="secondary" className="text-xs">
              {roleDisplayName(profile.primary_role)}
            </Badge>
          )}
        </div>
        
        {/* Last seen */}
        <p className="text-xs text-muted-foreground mt-2">
          Laatst gezien: {lastSeenLabel}
        </p>
      </div>
    </div>
  );
}



