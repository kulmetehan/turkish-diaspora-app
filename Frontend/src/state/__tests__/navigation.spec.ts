import { beforeEach, describe, expect, it } from "vitest";
import {
    __resetNavigationState,
    navigationActions,
    useActiveTab,
    useEventsNavigation,
    useMapNavigation,
    useNavigationState,
    useNewsNavigation,
} from "../navigation";

describe("navigation store", () => {
    beforeEach(() => {
        __resetNavigationState();
    });

    describe("initial state", () => {
        it("should have correct default values", () => {
            const state = useNavigationState();

            expect(state.map).toEqual({
                camera: null,
                selectedLocationId: null,
                filters: {
                    search: "",
                    category: "all",
                },
                listScrollTop: 0,
            });

            expect(state.news).toEqual({
                feed: "nl",
                categories: [],
                searchQuery: "",
                scrollTop: 0,
            });

            expect(state.events).toEqual({
                viewMode: "list",
                selectedId: null,
                detailId: null,
                scrollTop: 0,
            });

            expect(state.activeTab).toBe("map");
        });
    });

    describe("setMap", () => {
        it("should update map camera", () => {
            const camera = {
                center: [4.4777, 51.9244] as [number, number],
                zoom: 12,
                bearing: 0,
                pitch: 0,
            };

            navigationActions.setMap({ camera });

            const mapState = useMapNavigation();
            expect(mapState.camera).toEqual(camera);
            expect(mapState.selectedLocationId).toBeNull();
            expect(mapState.filters).toEqual({
                search: "",
                category: "all",
            });
        });

        it("should update map filters partially", () => {
            navigationActions.setMap({
                filters: {
                    search: "test",
                    category: "restaurant",
                },
            });

            const mapState = useMapNavigation();
            expect(mapState.filters).toEqual({
                search: "test",
                category: "restaurant",
            });
            expect(mapState.camera).toBeNull();
        });

        it("should update selectedLocationId", () => {
            navigationActions.setMap({ selectedLocationId: "loc-123" });

            const mapState = useMapNavigation();
            expect(mapState.selectedLocationId).toBe("loc-123");
        });

        it("should update listScrollTop", () => {
            navigationActions.setMap({ listScrollTop: 500 });

            const mapState = useMapNavigation();
            expect(mapState.listScrollTop).toBe(500);
        });

        it("should merge partial updates", () => {
            navigationActions.setMap({ selectedLocationId: "loc-1" });
            navigationActions.setMap({ listScrollTop: 100 });

            const mapState = useMapNavigation();
            expect(mapState.selectedLocationId).toBe("loc-1");
            expect(mapState.listScrollTop).toBe(100);
            expect(mapState.filters).toEqual({
                search: "",
                category: "all",
            });
        });
    });

    describe("setNews", () => {
        it("should update news feed", () => {
            navigationActions.setNews({ feed: "trending" });

            const newsState = useNewsNavigation();
            expect(newsState.feed).toBe("trending");
            expect(newsState.categories).toEqual([]);
            expect(newsState.searchQuery).toBe("");
        });

        it("should update categories", () => {
            navigationActions.setNews({ categories: ["sport", "economie"] });

            const newsState = useNewsNavigation();
            expect(newsState.categories).toEqual(["sport", "economie"]);
            expect(newsState.feed).toBe("nl");
        });

        it("should update searchQuery", () => {
            navigationActions.setNews({ searchQuery: "test query" });

            const newsState = useNewsNavigation();
            expect(newsState.searchQuery).toBe("test query");
        });

        it("should update scrollTop", () => {
            navigationActions.setNews({ scrollTop: 300 });

            const newsState = useNewsNavigation();
            expect(newsState.scrollTop).toBe(300);
        });

        it("should merge partial updates", () => {
            navigationActions.setNews({ feed: "local" });
            navigationActions.setNews({ categories: ["sport"] });

            const newsState = useNewsNavigation();
            expect(newsState.feed).toBe("local");
            expect(newsState.categories).toEqual(["sport"]);
            expect(newsState.searchQuery).toBe("");
        });
    });

    describe("setEvents", () => {
        it("should update viewMode", () => {
            navigationActions.setEvents({ viewMode: "map" });

            const eventsState = useEventsNavigation();
            expect(eventsState.viewMode).toBe("map");
            expect(eventsState.selectedId).toBeNull();
        });

        it("should update selectedId", () => {
            navigationActions.setEvents({ selectedId: 42 });

            const eventsState = useEventsNavigation();
            expect(eventsState.selectedId).toBe(42);
            expect(eventsState.detailId).toBeNull();
        });

        it("should update detailId", () => {
            navigationActions.setEvents({ detailId: 99 });

            const eventsState = useEventsNavigation();
            expect(eventsState.detailId).toBe(99);
            expect(eventsState.selectedId).toBeNull();
        });

        it("should update scrollTop", () => {
            navigationActions.setEvents({ scrollTop: 200 });

            const eventsState = useEventsNavigation();
            expect(eventsState.scrollTop).toBe(200);
        });

        it("should merge partial updates", () => {
            navigationActions.setEvents({ viewMode: "map" });
            navigationActions.setEvents({ selectedId: 10, detailId: 10 });

            const eventsState = useEventsNavigation();
            expect(eventsState.viewMode).toBe("map");
            expect(eventsState.selectedId).toBe(10);
            expect(eventsState.detailId).toBe(10);
        });
    });

    describe("state isolation", () => {
        it("should not affect other tabs when updating map", () => {
            const initialNews = useNewsNavigation();
            const initialEvents = useEventsNavigation();

            navigationActions.setMap({
                camera: {
                    center: [4.4777, 51.9244],
                    zoom: 10,
                    bearing: 0,
                    pitch: 0,
                },
                selectedLocationId: "loc-123",
            });

            const newsState = useNewsNavigation();
            const eventsState = useEventsNavigation();

            expect(newsState).toEqual(initialNews);
            expect(eventsState).toEqual(initialEvents);
        });

        it("should not affect other tabs when updating news", () => {
            const initialMap = useMapNavigation();
            const initialEvents = useEventsNavigation();

            navigationActions.setNews({
                feed: "trending",
                categories: ["sport"],
                searchQuery: "test",
            });

            const mapState = useMapNavigation();
            const eventsState = useEventsNavigation();

            expect(mapState).toEqual(initialMap);
            expect(eventsState).toEqual(initialEvents);
        });

        it("should not affect other tabs when updating events", () => {
            const initialMap = useMapNavigation();
            const initialNews = useNewsNavigation();

            navigationActions.setEvents({
                viewMode: "map",
                selectedId: 99,
                detailId: 99,
            });

            const mapState = useMapNavigation();
            const newsState = useNewsNavigation();

            expect(mapState).toEqual(initialMap);
            expect(newsState).toEqual(initialNews);
        });
    });

    describe("hooks", () => {
        it("should return full state from useNavigationState", () => {
            navigationActions.setMap({ selectedLocationId: "loc-1" });
            navigationActions.setNews({ feed: "trending" });
            navigationActions.setEvents({ viewMode: "map" });

            const fullState = useNavigationState();
            expect(fullState.map.selectedLocationId).toBe("loc-1");
            expect(fullState.news.feed).toBe("trending");
            expect(fullState.events.viewMode).toBe("map");
        });

        it("should return only map state from useMapNavigation", () => {
            navigationActions.setMap({ selectedLocationId: "loc-1" });
            navigationActions.setNews({ feed: "trending" });

            const mapState = useMapNavigation();
            expect(mapState.selectedLocationId).toBe("loc-1");
            expect(mapState).not.toHaveProperty("feed");
        });

        it("should return only news state from useNewsNavigation", () => {
            navigationActions.setNews({ feed: "trending" });
            navigationActions.setMap({ selectedLocationId: "loc-1" });

            const newsState = useNewsNavigation();
            expect(newsState.feed).toBe("trending");
            expect(newsState).not.toHaveProperty("selectedLocationId");
        });

        it("should return only events state from useEventsNavigation", () => {
            navigationActions.setEvents({ viewMode: "map" });
            navigationActions.setMap({ selectedLocationId: "loc-1" });

            const eventsState = useEventsNavigation();
            expect(eventsState.viewMode).toBe("map");
            expect(eventsState).not.toHaveProperty("selectedLocationId");
        });
    });

    describe("activeTab", () => {
        it("should default to 'map'", () => {
            const activeTab = useActiveTab();
            expect(activeTab).toBe("map");
        });

        it("should update activeTab with setActiveTab", () => {
            navigationActions.setActiveTab("news");

            const activeTab = useActiveTab();
            expect(activeTab).toBe("news");
        });

        it("should not update if same tab is set", () => {
            navigationActions.setActiveTab("map");
            const tab1 = useActiveTab();

            navigationActions.setActiveTab("map");
            const tab2 = useActiveTab();

            expect(tab1).toBe("map");
            expect(tab2).toBe("map");
        });

        it("should allow switching between tabs", () => {
            navigationActions.setActiveTab("news");
            expect(useActiveTab()).toBe("news");

            navigationActions.setActiveTab("events");
            expect(useActiveTab()).toBe("events");

            navigationActions.setActiveTab("map");
            expect(useActiveTab()).toBe("map");
        });
    });

    describe("news defaults safety", () => {
        it("should always return defined values for news feed", () => {
            const newsState = useNewsNavigation();
            expect(newsState.feed).toBeDefined();
            expect(typeof newsState.feed).toBe("string");
            expect(newsState.feed.length).toBeGreaterThan(0);
        });

        it("should always return an array for categories", () => {
            const newsState = useNewsNavigation();
            expect(Array.isArray(newsState.categories)).toBe(true);
        });

        it("should always return a string for searchQuery", () => {
            const newsState = useNewsNavigation();
            expect(typeof newsState.searchQuery).toBe("string");
        });

        it("should always return a number for scrollTop", () => {
            const newsState = useNewsNavigation();
            expect(typeof newsState.scrollTop).toBe("number");
            expect(newsState.scrollTop).toBeGreaterThanOrEqual(0);
        });
    });
});

