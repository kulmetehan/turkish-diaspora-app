import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { AppViewportShell, PageShell } from "@/components/layout";
import { ActivityFeed } from "@/components/feed/ActivityFeed";
import { DiasporaPulseLite } from "@/components/trending/DiasporaPulseLite";
import { PollsFeed } from "@/components/polls/PollsFeed";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { BulletinFeed } from "@/components/bulletin/BulletinFeed";
import { CreateBulletinPostDialog } from "@/components/bulletin/CreateBulletinPostDialog";
import { BulletinPostDetail } from "@/components/bulletin/BulletinPostDetail";
import { getBulletinPost } from "@/lib/api/bulletin";
import type { ActivityItem } from "@/lib/api";
import type { BulletinPost } from "@/types/bulletin";

type ActivityFilter = "all" | ActivityItem["activity_type"];

export default function FeedPage() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<"activity" | "trending" | "polls" | "bulletin">("activity");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedPost, setSelectedPost] = useState<BulletinPost | null>(null);
  const [showPostDetail, setShowPostDetail] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Handle URL parameters for bulletin post navigation
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tabParam = params.get('tab');
    const postParam = params.get('post');
    
    if (tabParam === 'bulletin') {
      setActiveTab('bulletin');
      if (postParam) {
        // Fetch and show bulletin post detail
        const postId = parseInt(postParam, 10);
        if (!isNaN(postId)) {
          getBulletinPost(postId)
            .then((post) => {
              setSelectedPost(post);
              setShowPostDetail(true);
            })
            .catch((error) => {
              console.error('Failed to load bulletin post:', error);
            });
        }
      }
    }
  }, [location.search]);

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Feed"
        subtitle="Activiteit en trending locaties van de Turkish diaspora community"
        maxWidth="4xl"
      >
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "activity" | "trending" | "polls" | "bulletin")} className="w-full">
          <div className="flex items-center justify-between mb-6">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="activity">Activiteit</TabsTrigger>
              <TabsTrigger value="trending">Trending</TabsTrigger>
              <TabsTrigger value="polls">Polls</TabsTrigger>
              <TabsTrigger value="bulletin">Prikbord</TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="activity" className="mt-0">
            <div className="space-y-4">
              <Tabs value={activityFilter} onValueChange={(v) => setActivityFilter(v as ActivityFilter)}>
                <TabsList className="overflow-x-auto bg-card mb-4">
                  <TabsTrigger value="all">Alles</TabsTrigger>
                  <TabsTrigger value="check_in">Check-ins</TabsTrigger>
                  <TabsTrigger value="reaction">Reacties</TabsTrigger>
                  <TabsTrigger value="note">Notities</TabsTrigger>
                  <TabsTrigger value="poll_response">Polls</TabsTrigger>
                  <TabsTrigger value="favorite">Favorieten</TabsTrigger>
                  <TabsTrigger value="bulletin_post">Advertenties</TabsTrigger>
                </TabsList>
                
                <TabsContent value="all" className="mt-0">
                  <ActivityFeed />
                </TabsContent>
                
                <TabsContent value="check_in" className="mt-0">
                  <ActivityFeed activityType="check_in" />
                </TabsContent>
                
                <TabsContent value="reaction" className="mt-0">
                  <ActivityFeed activityType="reaction" />
                </TabsContent>
                
                <TabsContent value="note" className="mt-0">
                  <ActivityFeed activityType="note" />
                </TabsContent>
                
                <TabsContent value="poll_response" className="mt-0">
                  <ActivityFeed activityType="poll_response" />
                </TabsContent>
                
                <TabsContent value="favorite" className="mt-0">
                  <ActivityFeed activityType="favorite" />
                </TabsContent>
                
                <TabsContent value="bulletin_post" className="mt-0">
                  <ActivityFeed activityType="bulletin_post" />
                </TabsContent>
              </Tabs>
            </div>
          </TabsContent>
          
          <TabsContent value="trending" className="mt-0">
            <DiasporaPulseLite />
          </TabsContent>
          
          <TabsContent value="polls" className="mt-0">
            <PollsFeed limit={10} />
          </TabsContent>
          
          <TabsContent value="bulletin" className="mt-0">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold">Prikbord</h2>
                  <p className="text-sm text-muted-foreground">
                    Plaats en bekijk advertenties van de Turkish diaspora gemeenschap
                  </p>
                </div>
                <Button onClick={() => setShowCreateDialog(true)}>
                  <Icon name="Plus" className="h-4 w-4 mr-2" />
                  Plaats advertentie
                </Button>
              </div>
              <BulletinFeed
                key={refreshKey}
                onPostClick={(post) => {
                  setSelectedPost(post);
                  setShowPostDetail(true);
                }}
              />
            </div>
          </TabsContent>
        </Tabs>
        
        <CreateBulletinPostDialog
          open={showCreateDialog}
          onOpenChange={setShowCreateDialog}
          onSuccess={() => {
            setRefreshKey((k) => k + 1);
          }}
        />
        
        <BulletinPostDetail
          post={selectedPost}
          open={showPostDetail}
          onOpenChange={setShowPostDetail}
          onDelete={() => {
            setRefreshKey((k) => k + 1);
          }}
        />
      </PageShell>
    </AppViewportShell>
  );
}

