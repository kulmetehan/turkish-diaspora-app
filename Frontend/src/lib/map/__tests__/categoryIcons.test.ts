import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import type { Map as MapboxMap } from "mapbox-gl";

import {
  CATEGORY_ICON_BASE_SIZE,
  CATEGORY_ICON_IDS,
  DEFAULT_ICON_ID,
  __test_buildLucideSvg,
  __test_getCategorySvg,
  ensureCategoryIcons,
  registerIconIfMissing,
} from "@/lib/map/categoryIcons";

class MapStub {
  images = new Map<string, { image: unknown; options: unknown }>();
  private onceHandlers = new Map<string, Function[]>();
  private styleLoaded = true;
  private styleKey = "test-style";

  hasImage(id: string) {
    return this.images.has(id);
  }

  addImage(id: string, image: unknown, options: unknown) {
    this.images.set(id, { image, options });
  }

  isStyleLoaded() {
    return this.styleLoaded;
  }

  setStyleLoaded(value: boolean) {
    this.styleLoaded = value;
  }

  getStyle() {
    return {
      sprite: this.styleKey,
      name: this.styleKey,
      sources: {},
    };
  }

  once(event: string, handler: Function) {
    const handlers = this.onceHandlers.get(event) ?? [];
    handlers.push(handler);
    this.onceHandlers.set(event, handlers);
  }

  trigger(event: string) {
    const handlers = this.onceHandlers.get(event) ?? [];
    this.onceHandlers.set(event, []);
    handlers.forEach((fn) => fn());
  }

  on() {
    /* noop */
  }

  triggerRepaint() {
    /* noop */
  }
}

const originalCreateElement = document.createElement.bind(document);
const originalImage = (globalThis as any).Image;
let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.stubGlobal(
    "createImageBitmap",
    vi.fn(async () => ({ close: vi.fn() }) as unknown as ImageBitmap),
  );

  class FakeImage {
    decoding = "sync";
    onload: (() => void) | null = null;
    onerror: ((err?: unknown) => void) | null = null;
    #src = "";

    get src() {
      return this.#src;
    }

    set src(value: string) {
      this.#src = value;
      queueMicrotask(() => {
        if (this.onload) {
          this.onload();
        }
      });
    }

    async decode(): Promise<void> {
      return Promise.resolve();
    }
  }

  vi.stubGlobal("Image", FakeImage as unknown as typeof Image);

  vi.spyOn(document, "createElement").mockImplementation((tagName: string): any => {
    if (tagName === "canvas") {
      const mockCtx = {
        scale: vi.fn(),
        clearRect: vi.fn(),
        drawImage: vi.fn(),
        save: vi.fn(),
        restore: vi.fn(),
        beginPath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        stroke: vi.fn(),
        fill: vi.fn(),
        arc: vi.fn(),
        ellipse: vi.fn(),
        quadraticCurveTo: vi.fn(),
        createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
        setTransform: vi.fn(),
        fillStyle: "",
        strokeStyle: "",
        lineWidth: 0,
      };
      return {
        width: 0,
        height: 0,
        getContext: vi.fn(() => mockCtx),
      } as unknown as HTMLCanvasElement;
    }
    return originalCreateElement(tagName);
  });

  createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockImplementation(() => "blob:mock");
  revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
  if (originalImage) {
    (globalThis as any).Image = originalImage;
  } else {
    delete (globalThis as any).Image;
  }
  createObjectURLSpy.mockRestore();
  revokeObjectURLSpy.mockRestore();
  vi.restoreAllMocks();
});

describe("category icon registration", () => {
  it("registers all category icons and default icon when style is loaded", async () => {
    const map = new MapStub();

    await ensureCategoryIcons(map as unknown as MapboxMap);

    for (const id of CATEGORY_ICON_IDS) {
      expect(map.hasImage(id)).toBe(true);
    }
    expect(map.hasImage(DEFAULT_ICON_ID)).toBe(true);
  });

  it("defers registration until style loads", async () => {
    const map = new MapStub();
    map.setStyleLoaded(false);

    const promise = ensureCategoryIcons(map as unknown as MapboxMap);

    expect(map.images.size).toBe(0);

    map.setStyleLoaded(true);
    map.trigger("style.load");
    await promise;

    expect(map.images.size).toBeGreaterThan(0);
  });

  it("registerIconIfMissing caches the same DPR result", async () => {
    const map = new MapStub();
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><circle cx="24" cy="24" r="22" fill="#000"/></svg>`;

    await registerIconIfMissing(
      map as unknown as MapboxMap,
      "test-icon",
      svg,
      CATEGORY_ICON_BASE_SIZE,
      2,
    );

    expect(map.hasImage("test-icon")).toBe(true);
    expect((map.images.get("test-icon")?.image as any)?.close).toBeDefined();

    await registerIconIfMissing(
      map as unknown as MapboxMap,
      "test-icon",
      svg,
      CATEGORY_ICON_BASE_SIZE,
      2,
    );
    expect(map.images.size).toBe(1);
  });
});

describe("buildLucideSvg", () => {
  it("resolves aliases for kebab-case lucide icon names", () => {
    const svg = __test_buildLucideSvg("utensils");
    expect(svg).toContain("<svg");
    expect(svg).not.toContain('d="M12 2v20M2 12h20"');
    const firstPath = svg.match(/<path[^>]*d="([^"]+)"/);
    expect(firstPath?.[1]).toBe("M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2");
  });

  it("wraps glyphs in scaled white stroke group", () => {
    const svg = __test_getCategorySvg("restaurant");
    expect(svg).toBeDefined();
    expect(svg).toContain('fill="#E30A17"');
    expect(svg).toContain('stroke="#FFFFFF"');
    expect(svg).toMatch(/transform="translate\(12 12\) scale\(0\.7\) translate\(-12 -12\)"/);
  });
});

