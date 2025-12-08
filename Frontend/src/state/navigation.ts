// Frontend/src/state/navigation.ts
//
// Navigation state store for preserving tab state across navigation.
// Uses React 18's useSyncExternalStore for safe subscriptions.
// This keeps Map, News, and Events tab state (camera, selections, filters, scroll positions) in ONE place.
//

import type { NewsCategoryKey } from "@/lib/routing/newsCategories";
import type { NewsFeedKey } from "@/lib/routing/newsFeed";
import { useSyncExternalStore } from "react";

// ---------- Types ----------

export type MapCamera = {
    center: [number, number];
    zoom: number;
    bearing: number;
    pitch: number;
};

export type MapFilters = {
    search: string;
    category: string | null;
};

export interface MapNavigationState {
    /** Map camera state (center, zoom, bearing, pitch). Null means use initial center from geolocation/fallback. */
    camera: MapCamera | null;
    /** Currently selected location id. */
    selectedLocationId: string | null;
    /** Active filters (search, category). */
    filters: MapFilters;
    /** Scroll position of the location list. */
    listScrollTop: number;
}

export interface NewsNavigationState {
    /** Active news feed key. */
    feed: NewsFeedKey;
    /** Active category filters. */
    categories: NewsCategoryKey[];
    /** Search query string. */
    searchQuery: string;
    /** Scroll position of the news list. */
    scrollTop: number;
}

export interface EventsNavigationState {
    /** View mode: list or map. */
    viewMode: "list" | "map";
    /** Currently selected event id. */
    selectedId: number | null;
    /** Currently opened detail event id. */
    detailId: number | null;
    /** Scroll position of the events list. */
    scrollTop: number;
}

export type TabId = "map" | "news" | "events" | "feed" | "account";

export interface NavigationState {
    activeTab: TabId;
    map: MapNavigationState;
    news: NewsNavigationState;
    events: EventsNavigationState;
}

// ---------- Internal store implementation ----------

const listeners = new Set<() => void>();

// Default navigation state
let state: NavigationState = {
    activeTab: "map",
    map: {
        camera: null,
        selectedLocationId: null,
        filters: {
            search: "",
            category: "all",
        },
        listScrollTop: 0,
    },
    news: {
        feed: "nl",
        categories: ["general"],
        searchQuery: "",
        scrollTop: 0,
    },
    events: {
        viewMode: "list",
        selectedId: null,
        detailId: null,
        scrollTop: 0,
    },
};

function emit() {
    for (const fn of Array.from(listeners)) fn();
}

function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

function getSnapshot(): NavigationState {
    return state;
}

// ---------- Public actions ----------

/** Update map navigation state (shallow merge). */
function setMap(partial: Partial<MapNavigationState>) {
    state = {
        ...state,
        map: { ...state.map, ...partial },
    };
    emit();
}

/** Update news navigation state (shallow merge). */
function setNews(partial: Partial<NewsNavigationState>) {
    state = {
        ...state,
        news: { ...state.news, ...partial },
    };
    emit();
}

/** Update events navigation state (shallow merge). */
function setEvents(partial: Partial<EventsNavigationState>) {
    state = {
        ...state,
        events: { ...state.events, ...partial },
    };
    emit();
}

/** Set the active tab. */
function setActiveTab(tab: TabId) {
    if (state.activeTab === tab) return;
    state = {
        ...state,
        activeTab: tab,
    };
    emit();
}

export const navigationActions = {
    setMap,
    setNews,
    setEvents,
    setActiveTab,
};

// ---------- Hooks ----------

/** Subscribe to the full navigation state. */
export function useNavigationState(): NavigationState {
    return useSyncExternalStore(subscribe, getSnapshot);
}

/** Subscribe to map navigation state only. */
export function useMapNavigation(): MapNavigationState {
    return useSyncExternalStore(subscribe, () => state.map);
}

/** Subscribe to news navigation state only. */
export function useNewsNavigation(): NewsNavigationState {
    return useSyncExternalStore(subscribe, () => state.news);
}

/** Subscribe to events navigation state only. */
export function useEventsNavigation(): EventsNavigationState {
    return useSyncExternalStore(subscribe, () => state.events);
}

/** Subscribe to active tab only. */
export function useActiveTab(): TabId {
    return useSyncExternalStore(subscribe, () => state.activeTab);
}

// ---------- Utilities (testing/dev) ----------

/** Reset to defaults (handy in tests). */
export function __resetNavigationState() {
    state = {
        activeTab: "map",
        map: {
            camera: null,
            selectedLocationId: null,
            filters: {
                search: "",
                category: "all",
                onlyTurkish: true,
            },
            listScrollTop: 0,
        },
        news: {
            feed: "nl",
            categories: ["general"],
            searchQuery: "",
            scrollTop: 0,
        },
        events: {
            viewMode: "list",
            selectedId: null,
            detailId: null,
            scrollTop: 0,
        },
    };
    emit();
}

