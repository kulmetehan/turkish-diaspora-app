import { useState } from "react";
import { AppViewportShell, PageShell } from "@/components/layout";
import { ActivityFeed } from "@/components/feed/ActivityFeed";
import { DiasporaPulseLite } from "@/components/trending/DiasporaPulseLite";
import { PollsFeed } from "@/components/polls/PollsFeed";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function FeedPage() {
  const [activeTab, setActiveTab] = useState<"activity" | "trending" | "polls">("activity");

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
            <ActivityFeed />
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

