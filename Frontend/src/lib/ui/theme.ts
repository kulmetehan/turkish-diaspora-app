export type ColorToken = `hsl(${string})`;

export const tokens = {
  color: {
    background: "hsl(var(--background))" as ColorToken,
    foreground: "hsl(var(--foreground))" as ColorToken,
    primary: "hsl(var(--primary))" as ColorToken,
    primaryFg: "hsl(var(--primary-foreground))" as ColorToken,
    secondary: "hsl(var(--secondary))" as ColorToken,
    secondaryFg: "hsl(var(--secondary-foreground))" as ColorToken,
    muted: "hsl(var(--muted))" as ColorToken,
    mutedFg: "hsl(var(--muted-foreground))" as ColorToken,
    destructive: "hsl(var(--destructive))" as ColorToken,
    destructiveFg: "hsl(var(--destructive-foreground))" as ColorToken,
    border: "hsl(var(--border))" as ColorToken,
    input: "hsl(var(--input))" as ColorToken,
    ring: "hsl(var(--ring))" as ColorToken,
    card: "hsl(var(--card))" as ColorToken,
    cardFg: "hsl(var(--card-foreground))" as ColorToken,
  },
  radius: {
    lg: "var(--radius-lg)",
    md: "var(--radius-md)",
    sm: "var(--radius-sm)",
  },
  shadow: {
    soft: "var(--shadow-soft)",
    card: "var(--shadow-card)",
  },
} as const;
