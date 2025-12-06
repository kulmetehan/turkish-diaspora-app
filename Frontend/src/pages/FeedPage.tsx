import { useState } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { ActivityFeed } from "@/components/feed/ActivityFeed";
import { DiasporaPulseLite } from "@/components/trending/DiasporaPulseLite";
import { PollsFeed } from "@/components/polls/PollsFeed";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ActivityItem } from "@/lib/api";

type ActivityFilter = "all" | ActivityItem["activity_type"];

export default function FeedPage() {
  const [activeTab, setActiveTab] = useState<"activity" | "trending" | "polls">("activity");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Feed"
        subtitle="Activiteit en trending locaties van de Turkish diaspora community"
        maxWidth="4xl"
      >
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "activity" | "trending" | "polls")} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="activity">Activiteit</TabsTrigger>
            <TabsTrigger value="trending">Trending</TabsTrigger>
            <TabsTrigger value="polls">Polls</TabsTrigger>
          </TabsList>
          
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
              </Tabs>
            </div>
          </TabsContent>
          
          <TabsContent value="trending" className="mt-0">
            <DiasporaPulseLite />
          </TabsContent>
          
          <TabsContent value="polls" className="mt-0">
            <PollsFeed limit={10} />
          </TabsContent>
        </Tabs>
      </PageShell>
    </AppViewportShell>
  );
}

