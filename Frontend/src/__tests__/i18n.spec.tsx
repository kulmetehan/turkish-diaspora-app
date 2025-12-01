import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot } from "react-dom/client";

import Filters from "@/components/Filters";

describe("i18n singleton", () => {
  beforeEach(() => {
    vi.resetModules();
    window.localStorage.clear();
  });

  it("initialises once with default nl and persists to localStorage", async () => {
    const mod = await import("@/i18n");
    expect(mod.initI18n()).toBe("nl");
    expect(window.localStorage.getItem("tda-language")).toBe("nl");

    window.localStorage.setItem("tda-language", "en");
    expect(mod.initI18n()).toBe("nl"); // already initialised, does not flip
    expect(mod.getCurrentLanguage()).toBe("nl");
  });

  it("allows language switch with normalisation and notifies subscribers", async () => {
    const mod = await import("@/i18n");
    mod.initI18n();

    const listener = vi.fn();
    const unsubscribe = mod.subscribeLanguage(listener);

    mod.setLanguage("EN-us");
    expect(mod.getCurrentLanguage()).toBe("en");
    expect(window.localStorage.getItem("tda-language")).toBe("en");
    expect(listener).toHaveBeenCalledWith("en");

    unsubscribe();
    mod.setLanguage("nl");
    expect(mod.getCurrentLanguage()).toBe("nl");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("keeps category sort stable regardless of label changes", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    const categoryOptions = [
      { key: "restaurant", label: "Restaurant" },
      { key: "bakery", label: "Bakkerij" },
      { key: "fast_food", label: "Fastfood" },
    ];

    await act(async () => {
      root.render(
        <Filters
          search=""
          category="all"
          onChange={() => undefined}
          categoryOptions={categoryOptions.slice().reverse()}
        />,
      );
    });

    const buttons = Array.from(container.querySelectorAll('button[role="option"]'));
    const labels = buttons
      .slice(1) // skip "Alle"
      .map((btn) => btn.textContent?.trim())
      .filter(Boolean);

    expect(labels).toEqual(["Bakkerij", "Fastfood", "Restaurant"]);

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });
});


