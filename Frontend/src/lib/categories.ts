// Frontend/src/lib/categories.ts

export function humanizeCategoryLabel(input: string | undefined | null): string {
  if (!input) return "—";

  let s = input as string;

  // Replace "_" and "/" with spaces (global)
  s = s.replace(/[_/]/g, " ");

  // Collapse multiple spaces and trim
  s = s.replace(/\s+/g, " ").trim();

  // Capitalize each word
  s = s
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");

  return s;
}


