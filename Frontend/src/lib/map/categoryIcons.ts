import type { LocationMarker } from "@/api/fetchLocations";
import type { Map as MapboxMap } from "mapbox-gl";

import { icons } from "lucide";

export const ICON_VERSION = "v2";
export const ICON_BASE_ID = `tda-marker-${ICON_VERSION}`;
export const FALLBACK_KEY = "other";
export const DEFAULT_ICON_ID = `${ICON_BASE_ID}-${FALLBACK_KEY}`;

// F4-S2: Snap-style marker design tokens
// Compact 32px markers with red base and white Lucide icons
export const MARKER_BASE_SIZE = 32; // Compact size, down from 48px
export const MARKER_FILL_DEFAULT = "#EF4444"; // red-500, Snap-style red
export const MARKER_FILL_SELECTED = "#DC2626"; // red-600, optional for future use
export const MARKER_ICON_COLOR = "#FFFFFF"; // white
export const MARKER_STROKE_COLOR = "rgba(0, 0, 0, 0.1)"; // subtle shadow
export const MARKER_BORDER_RADIUS = 8; // pill/rounded rect shape
export const MARKER_ICON_PADDING = 6; // inner padding for Lucide glyph
export const MARKER_ICON_SIZE = 16; // Lucide icon size within marker

export const CATEGORY_ICON_BASE_SIZE = MARKER_BASE_SIZE;

const CATEGORY_BACKGROUND = MARKER_FILL_DEFAULT;
const GLYPH_STROKE = MARKER_ICON_COLOR;
const GLYPH_SCALE = 0.5; // Adjusted for 16px icon in 32px marker (16/32 = 0.5)
const RIM_STROKE = MARKER_STROKE_COLOR;

type CategoryIconDefinition = {
  key: string;
  lucide: string;
  background: string;
  stroke: string;
};

const LUCIDE_ALIAS_MAP: Record<string, string> = {
  utensils: "Utensils",
  "shopping-cart": "ShoppingCart",
  croissant: "Croissant",
  beef: "Beef",
  scissors: "Scissors",
  coffee: "Coffee",
  "building-2": "Building2",
  "map-pin": "MapPin",
};

function resolveLucideName(name: string): string {
  const direct = icons[name];
  if (direct) {
    return name;
  }
  const lower = name.toLowerCase();
  const alias = LUCIDE_ALIAS_MAP[lower];
  if (alias && icons[alias]) {
    return alias;
  }
  const pascal = lower.replace(/(^|[-_])(\w)/g, (_, __, char: string) => char.toUpperCase());
  if (pascal && icons[pascal]) {
    return pascal;
  }
  return name;
}

const RAW_CATEGORY_CONFIG = [
  { key: "restaurant", lucide: "utensils" },
  { key: "supermarket", lucide: "shopping-cart" },
  { key: "bakery", lucide: "croissant" },
  { key: "butcher", lucide: "beef" },
  { key: "barber", lucide: "scissors" },
  { key: "cafe", lucide: "coffee" },
  { key: "mosque", lucide: "building-2" },
  { key: FALLBACK_KEY, lucide: "map-pin" },
] as const;

const CATEGORY_CONFIG: CategoryIconDefinition[] = RAW_CATEGORY_CONFIG.map((entry) => ({
  ...entry,
  background: CATEGORY_BACKGROUND,
  stroke: GLYPH_STROKE,
}));

const SVG_BY_KEY = new Map<string, string>();
const SVG_BY_ID = new Map<string, string>();

function buildLucideSvg(name: string, size = 24, strokeWidth = 2): string {
  const resolvedName = resolveLucideName(name);
  const node = icons[resolvedName];
  if (!node) {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M2 12h20"></path></svg>`;
  }
  const children = node
    .map(([tag, attrs]) => {
      const attrString = Object.entries(attrs)
        .map(([key, value]) => `${key}="${value}"`)
        .join(" ");
      return `<${tag} ${attrString}></${tag}>`;
    })
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round">${children}</svg>`;
}

/**
 * F4-S2: Build Snap-style marker SVG
 * Generates a compact rounded rectangle badge with red base and white Lucide icon.
 * Uses integer-based viewBox (0 0 32 32) to avoid sub-pixel blurring.
 */
function buildMarkerSvg(definition: CategoryIconDefinition): string {
  const lucideSvg = buildLucideSvg(definition.lucide);
  const inner = lucideSvg.replace(/^<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "");
  const size = MARKER_BASE_SIZE;
  const radius = MARKER_BORDER_RADIUS;
  const center = size / 2;
  
  // Calculate icon transform to center it with padding
  const iconSize = MARKER_ICON_SIZE;
  const iconScale = iconSize / 24; // Lucide icons are 24x24, scale to desired size
  
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <!-- Rounded rectangle background -->
  <rect x="0" y="0" width="${size}" height="${size}" rx="${radius}" ry="${radius}" fill="${definition.background}" />
  <!-- Subtle inner shadow/highlight -->
  <rect x="0" y="0" width="${size}" height="${size}" rx="${radius}" ry="${radius}" fill="none" stroke="${RIM_STROKE}" stroke-width="1" />
  <!-- Centered white Lucide icon -->
  <g stroke="${definition.stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <g transform="translate(${center} ${center}) scale(${iconScale}) translate(-12 -12)">
      ${inner}
    </g>
  </g>
</svg>`;
}

for (const definition of CATEGORY_CONFIG) {
  const svg = buildMarkerSvg(definition);
  SVG_BY_KEY.set(definition.key, svg);
  SVG_BY_ID.set(`${ICON_BASE_ID}-${definition.key}`, svg);
}
SVG_BY_ID.set(DEFAULT_ICON_ID, SVG_BY_KEY.get(FALLBACK_KEY)!);

const BITMAP_CACHE = new Map<string, Promise<ImageBitmap>>();
const REGISTRATION_INFLIGHT = new WeakMap<MapboxMap, Map<number, Promise<void>>>();
const STYLE_MISSING_ATTACHED = new WeakSet<MapboxMap>();
const STYLE_EXECUTED = new WeakMap<MapboxMap, Set<string>>();

export function roundDPR(input: number): number {
  if (!Number.isFinite(input) || input <= 0) return 2;
  const clamped = Math.min(Math.max(input, 1), 3);
  return Math.round(clamped);
}

export async function renderSvgToCanvas(svg: string, size: number, dpr: number): Promise<HTMLCanvasElement> {
  if (typeof document === "undefined") {
    throw new Error("renderSvgToCanvas requires a browser environment");
  }
  const pixelRatio = roundDPR(dpr);
  const width = Math.round(size * pixelRatio);
  const height = Math.round(size * pixelRatio);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Canvas 2D context unavailable");
  }
  if (typeof ctx.setTransform === "function") {
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  } else if (typeof (ctx as any).resetTransform === "function") {
    (ctx as any).resetTransform();
    ctx.scale(pixelRatio, pixelRatio);
  } else {
    ctx.scale(pixelRatio, pixelRatio);
  }
  ctx.clearRect(0, 0, size, size);

  const svgString = svg.includes("width=")
    ? svg
    : svg.replace("<svg ", `<svg width="${size}" height="${size}" `);

  const svgBlob = new Blob([svgString], { type: "image/svg+xml" });
  const url = URL.createObjectURL(svgBlob);

  try {
    const img = new Image();
    img.decoding = "sync";
    const loadPromise = new Promise<void>((resolve, reject) => {
      img.onload = () => {
        ctx.drawImage(img, 0, 0, size, size);
        resolve();
      };
      img.onerror = () => reject(new Error("Failed to decode SVG image."));
    });
    img.src = url;
    if (typeof img.decode === "function") {
      try {
        await img.decode();
      } catch {
        // ignore and rely on loadPromise
      }
    }
    await loadPromise;
  } finally {
    URL.revokeObjectURL(url);
  }

  return canvas;
}

export async function toBitmap(canvas: HTMLCanvasElement): Promise<ImageBitmap> {
  if (typeof createImageBitmap !== "function") {
    throw new Error("createImageBitmap is required for sprite registration.");
  }
  return createImageBitmap(canvas);
}

export async function registerIconIfMissing(
  map: MapboxMap,
  id: string,
  svg: string,
  size: number,
  dpr: number,
): Promise<void> {
  if (!map || typeof map.addImage !== "function") return;
  if (map.hasImage?.(id)) return;
  const cacheKey = `${id}@${dpr}`;
  let bitmapPromise = BITMAP_CACHE.get(cacheKey);
  if (!bitmapPromise) {
    bitmapPromise = (async () => {
      const canvas = await renderSvgToCanvas(svg, size, dpr);
      return toBitmap(canvas);
    })();
    BITMAP_CACHE.set(cacheKey, bitmapPromise);
  }
  const bitmap = await bitmapPromise;
  if (map.hasImage?.(id)) return;
  try {
    map.addImage(id, bitmap as any, { pixelRatio: dpr });
  } catch (error) {
    if (!(error instanceof Error) || !/Image with id/.test(error.message)) {
      throw error;
    }
  }
  map.triggerRepaint?.();
}

export async function registerAllCategoryIcons(map: MapboxMap, dpr: number): Promise<void> {
  const tasks: Promise<void>[] = [];
  for (const icon of CATEGORY_CONFIG) {
    const id = `${ICON_BASE_ID}-${icon.key}`;
    const svg = SVG_BY_ID.get(id);
    if (!svg) continue;
    tasks.push(registerIconIfMissing(map, id, svg, CATEGORY_ICON_BASE_SIZE, dpr));
  }
  const fallbackSvg = SVG_BY_ID.get(DEFAULT_ICON_ID);
  if (fallbackSvg) {
    tasks.push(registerIconIfMissing(map, DEFAULT_ICON_ID, fallbackSvg, CATEGORY_ICON_BASE_SIZE, dpr));
  }
  await Promise.all(tasks);
  if (typeof process !== "undefined" && process.env.NODE_ENV !== "production") {
    const sample = CATEGORY_CONFIG[0];
    const sampleId = `${ICON_BASE_ID}-${sample.key}`;
    const sampleSvg = SVG_BY_ID.get(sampleId);
    if (sampleSvg) {
      console.debug(
        `[categoryIcons] registered sample ${sampleId}: ${sampleSvg.slice(0, 60)}${sampleSvg.length > 60 ? "…" : ""}`,
      );
    }
  }
}

export function normalizeCategoryKey(raw?: string | null): string {
  const fallback = FALLBACK_KEY;
  if (typeof raw !== "string") return fallback;
  const trimmed = raw.trim().toLowerCase();
  if (!trimmed) return fallback;
  const sanitized = trimmed.replace(/[^a-z0-9_-]+/g, "_");
  if (!sanitized) return fallback;
  
  // Handle barbershop alias -> barber
  if (sanitized === "barbershop") {
    return "barber";
  }
  
  if (!SVG_BY_KEY.has(sanitized)) return fallback;
  return sanitized;
}

export function getCategoryIconId(key: string | null | undefined): string {
  const normalized = normalizeCategoryKey(key);
  return `${ICON_BASE_ID}-${normalized}`;
}

export function getCategoryIconIdForLocation(location: LocationMarker): string {
  const candidates = [
    typeof location.category_key === "string" ? location.category_key : null,
    typeof location.category === "string" ? location.category : null,
    typeof location.category_label === "string" ? location.category_label : null,
  ];
  for (const raw of candidates) {
    if (!raw) continue;
    const normalized = normalizeCategoryKey(raw);
    if (normalized !== FALLBACK_KEY) {
      return getCategoryIconId(normalized);
    }
  }
  return getCategoryIconId(FALLBACK_KEY);
}

export function ensureCategoryIcons(map: MapboxMap, pixelRatio?: number): Promise<void> {
  if (!map || typeof map.addImage !== "function") return Promise.resolve();
  const sourceDpr = typeof window !== "undefined" ? window.devicePixelRatio ?? 2 : 2;
  const dpr = roundDPR(pixelRatio ?? sourceDpr);

  let inflightByDpr = REGISTRATION_INFLIGHT.get(map);
  if (!inflightByDpr) {
    inflightByDpr = new Map<number, Promise<void>>();
    REGISTRATION_INFLIGHT.set(map, inflightByDpr);
  }
  const existing = inflightByDpr.get(dpr);
  if (existing) return existing;

  const promise = (async () => {
    if (!map.isStyleLoaded?.()) {
      await new Promise<void>((resolve) => {
        let resolved = false;
        const handler = () => {
          if (resolved) return;
          resolved = true;
          resolve();
        };
        map.once?.("style.load", handler as any);
        map.once?.("load", handler as any);
      });
    }
    let executed = STYLE_EXECUTED.get(map);
    if (!executed) {
      executed = new Set<string>();
      STYLE_EXECUTED.set(map, executed);
    }
    let styleKey = "default";
    if (typeof map.getStyle === "function") {
      try {
        const style = map.getStyle();
        if (style) {
          styleKey = `${style.sprite ?? ""}|${style.name ?? ""}|${Object.keys(style.sources ?? {}).join(",")}`;
        }
      } catch {
        // ignore
      }
    }
    if (styleKey && executed.has(styleKey)) {
      return;
    }
    await registerAllCategoryIcons(map, dpr);
    executed.add(styleKey);
  })().finally(() => {
    const current = REGISTRATION_INFLIGHT.get(map);
    if (current?.get(dpr) === promise) {
      current.delete(dpr);
    }
  });

  inflightByDpr.set(dpr, promise);
  return promise;
}

export function attachCategoryIconFallback(map: MapboxMap): void {
  if (!map || typeof map.on !== "function") return;
  if (STYLE_MISSING_ATTACHED.has(map)) return;

  map.on("styleimagemissing", (event: any) => {
    const id = typeof event?.id === "string" ? event.id : undefined;
    if (!id) return;
    const svg =
      SVG_BY_ID.get(id) ??
      (id === DEFAULT_ICON_ID ? SVG_BY_KEY.get(FALLBACK_KEY) : undefined);
    if (!svg) return;
    const sourceDpr = typeof window !== "undefined" ? window.devicePixelRatio ?? 2 : 2;
    const dpr = roundDPR(sourceDpr);
    void registerIconIfMissing(map, id, svg, CATEGORY_ICON_BASE_SIZE, dpr);
  });

  STYLE_MISSING_ATTACHED.add(map);
}

export const CATEGORY_ICON_IDS = CATEGORY_CONFIG.map((icon) => `${ICON_BASE_ID}-${icon.key}`);

export function __test_getCategorySvg(key: string): string | undefined {
  return SVG_BY_KEY.get(key);
}

export { buildLucideSvg as __test_buildLucideSvg };

