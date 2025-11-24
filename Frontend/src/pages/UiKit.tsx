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
    <div className="mx-auto max-w-5xl space-y-8 rounded-[40px] border border-white/10 bg-surface-raised/70 p-6 text-foreground shadow-soft backdrop-blur-2xl">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-brand-white">UI Kit</h1>
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
        <CardHeader><CardTitle>Brand Colors & Gradients</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-6 sm:grid-cols-3">
            <div className="flex flex-col items-center text-center">
              <div className="h-16 w-16 rounded-full border border-white/10 bg-brand-red shadow-card" />
              <span className="mt-2 text-sm font-medium text-brand-white">Brand Red</span>
              <span className="text-xs text-brand-white/70">Primary actions</span>
            </div>
            <div className="flex flex-col items-center text-center">
              <div className="h-16 w-16 rounded-full border border-white/10 bg-brand-redSoft shadow-card" />
              <span className="mt-2 text-sm font-medium text-brand-white">Brand Red Soft</span>
              <span className="text-xs text-brand-white/70">Hover + chips</span>
            </div>
            <div className="flex flex-col items-center text-center">
              <div className="h-16 w-16 rounded-full border border-white/20 bg-brand-white shadow-card" />
              <span className="mt-2 text-sm font-medium text-brand-white">Brand White</span>
              <span className="text-xs text-brand-white/70">Text on red</span>
            </div>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-gradient-main p-4 text-brand-white shadow-card">
              <span className="text-sm font-semibold uppercase tracking-wide">Gradient Main</span>
              <span className="text-xs text-brand-white/80">Hero backgrounds</span>
            </div>
            <div className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-gradient-nav p-4 text-brand-white shadow-card">
              <span className="text-sm font-semibold uppercase tracking-wide">Gradient Nav</span>
              <span className="text-xs text-brand-white/80">Footer + overlays</span>
            </div>
            <div className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-gradient-card p-4 text-brand-white shadow-card">
              <span className="text-sm font-semibold uppercase tracking-wide">Gradient Card</span>
              <span className="text-xs text-brand-white/80">Cards & chips</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Surfaces</CardTitle></CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-3xl border border-white/10 bg-brand-surface p-4 text-brand-white shadow-soft">
            <h3 className="text-sm font-semibold uppercase tracking-wide">Brand Surface</h3>
            <p className="text-xs text-brand-white/80">App shell &amp; body gradient</p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-brand-surface-alt p-4 text-brand-white shadow-soft">
            <h3 className="text-sm font-semibold uppercase tracking-wide">Surface Alt</h3>
            <p className="text-xs text-brand-white/80">Panels &amp; overlays</p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-surface-raised/80 p-4 text-foreground shadow-soft">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-brand-white">Muted Surface</h3>
            <p className="text-xs text-brand-white/70">Cards inside overlays</p>
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
            <TabsList className="grid w-full grid-cols-2 rounded-2xl border border-white/10 bg-surface-muted/70 p-1 text-brand-white/70 shadow-inner">
              <TabsTrigger
                value="one"
                className="flex items-center justify-center gap-2 rounded-xl py-2 data-[state=active]:bg-gradient-card data-[state=active]:text-brand-white"
              >
                <Icon name="MapPin" className="h-4 w-4" />
                Map
              </TabsTrigger>
              <TabsTrigger
                value="two"
                className="flex items-center justify-center gap-2 rounded-xl py-2 data-[state=active]:bg-gradient-card data-[state=active]:text-brand-white"
              >
                <Icon name="List" className="h-4 w-4" />
                List
              </TabsTrigger>
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
