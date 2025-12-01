import { useEffect, useState } from "react";

import { AppViewportShell, PageShell } from "@/components/layout";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { getTheme, setTheme, type ThemeSetting } from "@/lib/theme/darkMode";

export default function AccountPage() {
  const [theme, setThemeState] = useState<ThemeSetting>("system");

  useEffect(() => {
    setThemeState(getTheme());
  }, []);

  const cycleTheme = () => {
    const order: ThemeSetting[] = ["light", "dark", "system"];
    const currentIndex = order.indexOf(theme);
    const next = order[(currentIndex >= 0 ? currentIndex + 1 : 0) % order.length];
    setThemeState(next);
    setTheme(next);
  };

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Account"
        subtitle="Profile tools and saved places will arrive here. For now, keep exploring the map."
        maxWidth="4xl"
      >
        <section
          aria-labelledby="appearance-heading"
          className="rounded-3xl border border-border bg-card p-6 shadow-soft"
        >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h2 id="appearance-heading" className="text-lg font-medium text-foreground">
              Appearance
            </h2>
            <p className="text-sm text-muted-foreground">
              Temporarily manage the theme from here while the header is removed.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={cycleTheme}
            aria-label="Schakel thema"
            className="inline-flex items-center gap-2"
          >
            <Icon name="SunMoon" className="h-4 w-4" aria-hidden />
            <span>Theme: {theme}</span>
          </Button>
        </div>
      </section>
      </PageShell>
    </AppViewportShell>
  );
}

