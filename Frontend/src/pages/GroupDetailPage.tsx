// Frontend/src/pages/GroupDetailPage.tsx
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  getGroup, 
  listGroupMembers,
  getGroupActivity,
  joinGroup,
  leaveGroup,
  type UserGroup,
  type GroupMember,
  type GroupActivity,
} from "@/lib/api";
import { toast } from "sonner";

export default function GroupDetailPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();
  const [group, setGroup] = useState<UserGroup | null>(null);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [activity, setActivity] = useState<GroupActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [isMember, setIsMember] = useState(false);

  useEffect(() => {
    if (groupId) {
      loadGroupData();
    }
  }, [groupId]);

  const loadGroupData = async () => {
    if (!groupId) return;
    
    setLoading(true);
    try {
      const [groupData, membersData, activityData] = await Promise.all([
        getGroup(Number(groupId)),
        listGroupMembers(Number(groupId)),
        getGroupActivity(Number(groupId)),
      ]);
      
      setGroup(groupData);
      setMembers(membersData);
      setActivity(activityData);
      
      // Check if current user is a member
      // In production, would check against authenticated user ID
      setIsMember(membersData.some(m => m.user_id === "current-user-id"));
    } catch (err) {
      toast.error("Failed to load group", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
      navigate("/groups");
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async () => {
    if (!groupId) return;
    
    try {
      await joinGroup(Number(groupId));
      toast.success("Joined group successfully");
      loadGroupData();
    } catch (err) {
      toast.error("Failed to join group", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  const handleLeave = async () => {
    if (!groupId) return;
    
    try {
      await leaveGroup(Number(groupId));
      toast.success("Left group successfully");
      navigate("/groups");
    } catch (err) {
      toast.error("Failed to leave group", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  if (loading) {
    return (
      <AppViewportShell variant="content">
        <PageShell title="Loading..." maxWidth="full">
          <Skeleton className="h-64 w-full" />
        </PageShell>
      </AppViewportShell>
    );
  }

  if (!group) {
    return null;
  }

  return (
    <AppViewportShell variant="content">
      <PageShell
        title={group.name}
        subtitle={group.description || "No description"}
        maxWidth="full"
      >
        <div className="space-y-6">
          {/* Group Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Group Information</CardTitle>
                {isMember ? (
                  <Button variant="destructive" onClick={handleLeave}>
                    Leave Group
                  </Button>
                ) : (
                  <Button onClick={handleJoin}>Join Group</Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Members</p>
                  <p className="text-2xl font-bold">{group.member_count}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="text-sm">{new Date(group.created_at).toLocaleDateString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Members */}
          <Card>
            <CardHeader>
              <CardTitle>Members</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {members.map((member) => (
                  <div key={member.id} className="flex items-center justify-between p-2 border rounded">
                    <div>
                      <p className="font-medium">User {member.user_id.slice(0, 8)}</p>
                      <p className="text-sm text-muted-foreground capitalize">{member.role}</p>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Joined {new Date(member.joined_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Activity Feed */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {activity.length > 0 ? (
                <div className="space-y-2">
                  {activity.map((item) => (
                    <div key={item.id} className="p-2 border rounded">
                      <p className="text-sm">
                        <span className="font-medium capitalize">{item.activity_type}</span>
                        {item.location_id && ` at Location #${item.location_id}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No recent activity</p>
              )}
            </CardContent>
          </Card>
        </div>
      </PageShell>
    </AppViewportShell>
  );
}


















