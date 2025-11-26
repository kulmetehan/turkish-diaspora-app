export default function FeedPage() {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10">
      <header>
        <h1 className="text-3xl font-semibold text-foreground">Feed</h1>
        <p className="text-base text-muted-foreground">
          We&apos;re curating stories and highlights from the Turkish diaspora. Stay tuned.
        </p>
      </header>
      <section className="rounded-3xl border border-border bg-card p-6 shadow-soft">
        <p className="text-base text-muted-foreground">
          We&apos;re curating stories and highlights from the Turkish diaspora. Stay tuned.
        </p>
      </section>
    </div>
  );
}

