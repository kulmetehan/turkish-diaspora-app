import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import { toast } from "sonner";

export default function UiKit() {
  const [value, setValue] = useState("");

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">UI Kit</h1>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => toast("Hello from toast!")}>
            Show Toast
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogTitle className="mb-2 text-lg font-semibold">Dialog Title</DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground">
                This is a sample dialog with focus trapping.
              </DialogDescription>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      <Card>
        <CardHeader><CardTitle>Brand Colors</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-6">
            <div className="flex flex-col items-center">
              <div className="h-16 w-16 rounded-full bg-brand-red shadow-card border border-border" />
              <span className="mt-2 text-sm font-medium">Brand Red</span>
              <span className="text-xs text-muted-foreground">Primary actions</span>
            </div>
            <div className="flex flex-col items-center">
              <div className="h-16 w-16 rounded-full bg-brand-redSoft shadow-card border border-border" />
              <span className="mt-2 text-sm font-medium">Brand Red Soft</span>
              <span className="text-xs text-muted-foreground">Gradients & backgrounds</span>
            </div>
            <div className="flex flex-col items-center">
              <div className="h-16 w-16 rounded-full bg-brand-white border-2 border-border shadow-card" />
              <span className="mt-2 text-sm font-medium">Brand White</span>
              <span className="text-xs text-muted-foreground">Text on brand red</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Buttons & Badges</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="link">Link</Button>
          </div>
          <div className="flex items-center gap-2">
            <Badge>Default (Brand Red)</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="outline">Outline</Badge>
          </div>
          <div className="pt-2 border-t">
            <p className="text-sm text-muted-foreground mb-2">Active chip example:</p>
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-red bg-brand-redSoft px-3 py-1.5 text-sm text-primary-foreground">
              <span>Active Category</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Forms</CardTitle></CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" placeholder="Your name" value={value} onChange={e => setValue(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Category</Label>
            <Select>
              <SelectTrigger>Pick one…</SelectTrigger>
              <SelectContent>
                <SelectItem value="bakery">Bakery</SelectItem>
                <SelectItem value="restaurant">Restaurant</SelectItem>
                <SelectItem value="supermarket">Supermarket</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Tabs & Icons</CardTitle></CardHeader>
        <CardContent>
          <Tabs defaultValue="one">
            <TabsList>
              <TabsTrigger value="one"><Icon name="MapPin" className="mr-2 h-4 w-4" />One</TabsTrigger>
              <TabsTrigger value="two"><Icon name="List" className="mr-2 h-4 w-4" />Two</TabsTrigger>
            </TabsList>
            <div className="mt-4">
              <TabsContent value="one">Tab One Content</TabsContent>
              <TabsContent value="two">Tab Two Content</TabsContent>
            </div>
          </Tabs>
        </CardContent>
      </Card>

      <section className="prose dark:prose-invert">
        <h2>Richtlijnen</h2>
        <ul>
          <li>Mobile-first; whitespace; korte labels; duidelijke focus states.</li>
          <li>≤200ms micro-animaties voor snelle perceptie.</li>
          <li>Gebruik de shared UI: <code>Button</code>, <code>Input</code>, … (geen ad-hoc styles).</li>
          <li>Icons via <code>&lt;Icon name="…"/&gt;</code> (lucide-react).</li>
          <li>Contrast ≥ WCAG AA.</li>
        </ul>
      </section>
    </div>
  );
}
