import { Button } from "@/components/ui/button";
import { setTheme, getTheme, type ThemeSetting } from "@/lib/theme/darkMode";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Icon";

export function Header() {
  const [theme, setState] = useState<ThemeSetting>("system");
  useEffect(() => setState(getTheme()), []);

  function cycle() {
    const order: ThemeSetting[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setState(next);
    setTheme(next);
  }

  return (
    <header className="flex items-center justify-between px-4 py-3 border-b bg-background/60 backdrop-blur">
      <div className="flex items-center gap-2">
        <Icon name="Map" className="h-5 w-5" aria-hidden />
        <span className="font-semibold">Turkish Diaspora App</span>
      </div>
      <nav className="flex items-center gap-2">
        <Button variant="ghost" asChild><a href="/">Home</a></Button>
        <Button variant="ghost" asChild><a href="/ui-kit">UI Kit</a></Button>
        <Button variant="outline" onClick={cycle} aria-label="Toggle theme">
          <Icon name="SunMoon" className="mr-2 h-4 w-4" />
          Theme: {theme}
        </Button>
      </nav>
    </header>
  );
}
