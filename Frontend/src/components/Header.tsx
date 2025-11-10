import { useEffect, useState } from "react";
import { NavLink, Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { setTheme, getTheme, type ThemeSetting } from "@/lib/theme/darkMode";

export function Header() {
  const [theme, setState] = useState<ThemeSetting>("system");

  useEffect(() => {
    setState(getTheme());
  }, []);

  function cycle() {
    const order: ThemeSetting[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setState(next);
    setTheme(next);
  }

  return (
    <header data-header className="w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto max-w-7xl flex items-center gap-3 p-3">
        {/* Logo / Home */}
        <Link to="/" className="inline-flex items-center gap-2 font-semibold">
          <Icon name="Map" aria-label="Logo" />
          <span>Turkish Diaspora App</span>
        </Link>

        {/* Nav rechts */}
        <nav className="ml-auto flex items-center gap-2">
          <Button variant="ghost" asChild>
            <NavLink
              to="/"
              className={({ isActive }) => (isActive ? "font-medium" : undefined)}
              end
            >
              Home
            </NavLink>
          </Button>

          <Button variant="ghost" asChild>
            <NavLink
              to="/ui-kit"
              className={({ isActive }) => (isActive ? "font-medium" : undefined)}
            >
              UI Kit
            </NavLink>
          </Button>

          <Button variant="outline" size="sm" onClick={cycle} aria-label="Toggle theme">
            <Icon name="SunMoon" className="mr-2 h-4 w-4" />
            Theme: {theme}
          </Button>
        </nav>
      </div>
    </header>
  );
}
