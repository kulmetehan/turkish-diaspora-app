import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        brand: {
          redStrong: "hsl(var(--brand-red-strong))",
          red: "hsl(var(--brand-red))",
          redSoft: "hsl(var(--brand-red-soft))",
          white: "hsl(var(--brand-white))",
          accent: "hsl(var(--brand-accent))",
          accentSoft: "hsl(var(--brand-accent-soft))",
        },
        surface: {
          base: "hsl(var(--surface-base))",
          raised: "hsl(var(--surface-raised))",
          card: "hsl(var(--surface-card))",
          muted: "hsl(var(--surface-muted))",
          contrast: "hsl(var(--surface-contrast))",
        },
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        card: "var(--shadow-card)",
      },
      spacing: {
        "grid-gutter": "var(--space-grid-gutter)",
      },
      backgroundImage: {
        "gradient-main": "var(--gradient-main)",
        "gradient-nav": "var(--gradient-nav)",
        "gradient-card": "var(--gradient-card)",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "scale-in": { from: { transform: "scale(.98)" }, to: { transform: "scale(1)" } },
      },
      animation: {
        "fade-in": "fade-in .15s ease-out",
        "scale-in": "scale-in .15s ease-out",
      },
    },
  },
  plugins: [],
} satisfies Config;
