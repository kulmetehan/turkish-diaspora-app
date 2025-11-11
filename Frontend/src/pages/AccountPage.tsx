import { useEffect, useState } from "react";

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
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold text-foreground">Account</h1>
        <p className="text-muted-foreground">
          Profile tools and saved places will arrive here. For now, keep exploring the map.
        </p>
      </header>

      <section
        aria-labelledby="appearance-heading"
        className="rounded-2xl border border-border/60 bg-card/80 p-4 shadow-sm supports-[backdrop-filter]:bg-card/70"
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
    </div>
  );
}

