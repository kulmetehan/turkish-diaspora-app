// Frontend/src/pages/GroupsPage.tsx
import { useState, useEffect } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  listGroups, 
  createGroup,
  joinGroup,
  type UserGroup,
} from "@/lib/api";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

export default function GroupsPage() {
  const [groups, setGroups] = useState<UserGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupDescription, setNewGroupDescription] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    loadGroups();
  }, [search]);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const data = await listGroups({ search, limit: 50 });
      setGroups(data);
    } catch (err) {
      toast.error("Failed to load groups", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) {
      toast.error("Group name is required");
      return;
    }

    try {
      const group = await createGroup({
        name: newGroupName,
        description: newGroupDescription || null,
        is_public: true,
      });
      
      toast.success("Group created successfully");
      setShowCreateForm(false);
      setNewGroupName("");
      setNewGroupDescription("");
      navigate(`/groups/${group.id}`);
    } catch (err) {
      toast.error("Failed to create group", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  const handleJoinGroup = async (groupId: number) => {
    try {
      await joinGroup(groupId);
      toast.success("Joined group successfully");
      loadGroups();
    } catch (err) {
      toast.error("Failed to join group", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="User Groups"
        subtitle="Join or create community groups"
        maxWidth="full"
      >
        <div className="space-y-6">
          {/* Search and Create */}
          <div className="flex items-center gap-4">
            <Input
              placeholder="Search groups..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
            <Button onClick={() => setShowCreateForm(!showCreateForm)}>
              Create Group
            </Button>
          </div>

          {/* Create Form */}
          {showCreateForm && (
            <Card>
              <CardHeader>
                <CardTitle>Create New Group</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  placeholder="Group name"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                />
                <Input
                  placeholder="Description (optional)"
                  value={newGroupDescription}
                  onChange={(e) => setNewGroupDescription(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button onClick={handleCreateGroup}>Create</Button>
                  <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Groups List */}
          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : groups.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {groups.map((group) => (
                <Card key={group.id} className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardHeader>
                    <CardTitle 
                      className="cursor-pointer"
                      onClick={() => navigate(`/groups/${group.id}`)}
                    >
                      {group.name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-4">
                      {group.description || "No description"}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        {group.member_count} members
                      </span>
                      <Button
                        size="sm"
                        onClick={() => handleJoinGroup(group.id)}
                      >
                        Join
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No groups found
              </CardContent>
            </Card>
          )}
        </div>
      </PageShell>
    </AppViewportShell>
  );
}

























