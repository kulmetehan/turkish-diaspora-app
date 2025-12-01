import { AppViewportShell, PageShell } from "@/components/layout";

export default function FeedPage() {
  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Feed"
        subtitle="We're curating stories and highlights from the Turkish diaspora. Stay tuned."
        maxWidth="4xl"
      >
        <section className="rounded-3xl border border-border bg-card p-6 shadow-soft">
          <p className="text-base text-muted-foreground">
            We&apos;re curating stories and highlights from the Turkish diaspora. Stay tuned.
          </p>
        </section>
      </PageShell>
    </AppViewportShell>
  );
}

