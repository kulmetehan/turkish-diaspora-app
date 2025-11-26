import { useCallback, useEffect, useMemo, useState } from "react";

import type { NewsCity, NewsCityList } from "@/api/news";
import { fetchNewsCities } from "@/api/news";

type CountryCode = "nl" | "tr";

export type CityPreferences = Record<CountryCode, string[]>;

export interface CityLabel {
    key: string;
    name: string;
    country: CountryCode;
    province?: string;
}

export type CityLabelMap = Record<string, CityLabel>;

const STORAGE_KEY = "tda.news.cityPrefs.v1";
const MAX_SELECTIONS = 2;

interface StoredCityPreferences {
    version: number;
    selections: CityPreferences;
    labels?: CityLabelMap;
}

type CityLookup = Record<string, NewsCity>;

type RememberSource =
    | NewsCityList
    | CityRecommendations
    | CityLabelMap
    | CityLabel[]
    | NewsCity[]
    | null;

export interface CityRecommendations {
    nl: NewsCity[];
    tr: NewsCity[];
}

export interface UseNewsCityPreferencesOptions {
    currentFeed?: "diaspora" | "nl" | "tr" | "local" | "origin" | "geo" | "trending" | "bookmarks";
}

export function useNewsCityPreferences(options?: UseNewsCityPreferencesOptions) {
    const currentFeed = options?.currentFeed;
    const [dataset, setDataset] = useState<NewsCityList | null>(null);
    const [preferences, setPreferences] = useState<CityPreferences>({ nl: [], tr: [] });
    const [cityLabels, setCityLabels] = useState<CityLabelMap>({});
    const [isModalOpen, setModalOpen] = useState(false);
    const [loading, setLoading] = useState(true);

    const cityLookup = useMemo(() => buildCityLookup(dataset), [dataset]);
    const recommendations = useMemo(() => deriveRecommendations(dataset), [dataset]);

    const rememberCityLabels = useCallback((source: RememberSource) => {
        if (!source) return;
        setCityLabels((prev) => {
            const next = { ...prev };
            let changed = false;
            const pushLabel = (label: CityLabel | null | undefined) => {
                if (!label) return;
                const normalizedKey = normalizeCityKey(label.key);
                if (!normalizedKey || next[normalizedKey]) return;
                next[normalizedKey] = {
                    key: normalizedKey,
                    name: label.name,
                    country: label.country,
                    province: label.province,
                };
                changed = true;
            };
            const appendFromNewsCities = (cities: NewsCity[]) => {
                cities.forEach((city) => pushLabel(toCityLabelFromNewsCity(city)));
            };
            if (Array.isArray(source)) {
                source.forEach((entry) => {
                    if ("cityKey" in entry) {
                        pushLabel(toCityLabelFromNewsCity(entry as NewsCity));
                    } else {
                        const label = entry as CityLabel;
                        pushLabel({
                            key: label.key,
                            name: label.name,
                            country: label.country,
                            province: label.province,
                        });
                    }
                });
            } else if (
                source &&
                typeof source === "object" &&
                "cities" in (source as NewsCityList) &&
                Array.isArray((source as NewsCityList).cities)
            ) {
                appendFromNewsCities((source as NewsCityList).cities);
            } else if (
                source &&
                typeof source === "object" &&
                Array.isArray((source as CityRecommendations).nl) &&
                Array.isArray((source as CityRecommendations).tr)
            ) {
                appendFromNewsCities((source as CityRecommendations).nl);
                appendFromNewsCities((source as CityRecommendations).tr);
            } else {
                Object.values(source as CityLabelMap).forEach((label) => pushLabel(label));
            }
            return changed ? next : prev;
        });
    }, []);

    useEffect(() => {
        let mounted = true;
        async function load() {
            try {
                const config = await fetchNewsCities();
                if (!mounted) return;
                setDataset(config);
                rememberCityLabels(config);
                const lookup = buildCityLookup(config);
                const stored = readStoredPreferences(lookup);
                if (stored) {
                    setPreferences(stored.selections);
                    setCityLabels((prev) => ({ ...prev, ...stored.labels }));
                    // Only open modal for local/origin feeds when cities are missing
                    if (currentFeed === "local" || currentFeed === "origin") {
                        if (
                            (currentFeed === "local" && !stored.selections.nl.length) ||
                            (currentFeed === "origin" && !stored.selections.tr.length)
                        ) {
                            setModalOpen(true);
                        }
                    }
                } else {
                    const defaults = buildDefaultPreferences(config, lookup);
                    setPreferences(defaults);
                    // Only open modal for local/origin feeds when no stored preferences exist
                    if (currentFeed === "local" || currentFeed === "origin") {
                        setModalOpen(true);
                    }
                }
            } catch (error) {
                console.error("Failed to load news city config", error);
                const defaults = buildDefaultPreferences(null);
                setPreferences(defaults);
                // Only open modal for local/origin feeds on error
                if (currentFeed === "local" || currentFeed === "origin") {
                    setModalOpen(true);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }
        void load();
        return () => {
            mounted = false;
        };
    }, [rememberCityLabels, currentFeed]);

    const savePreferences = useCallback(
        (next: CityPreferences) => {
            setPreferences(next);
            const keysToPersist = new Set([...next.nl, ...next.tr]);
            const filteredLabels: CityLabelMap = {};
            keysToPersist.forEach((key) => {
                const normalized = key.toLowerCase();
                if (cityLabels[normalized]) {
                    filteredLabels[normalized] = cityLabels[normalized];
                }
            });
            const payload: StoredCityPreferences = {
                version: 2,
                selections: next,
                labels: filteredLabels,
            };
            try {
                window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
            } catch {
                // ignore
            }
            setModalOpen(false);
        },
        [cityLabels],
    );

    const openModal = useCallback(() => setModalOpen(true), []);
    const closeModal = useCallback(() => setModalOpen(false), []);

    const ready = useMemo(() => Boolean(dataset) && !loading, [dataset, loading]);

    return {
        options: recommendations,
        preferences,
        cityLabels,
        loading,
        ready,
        isModalOpen,
        openModal,
        closeModal,
        savePreferences,
        rememberCityLabels,
    };
}

function readStoredPreferences(cityLookup?: CityLookup): { selections: CityPreferences; labels: CityLabelMap } | null {
    if (typeof window === "undefined") return null;
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed) return null;
        if (Array.isArray(parsed.nl) && Array.isArray(parsed.tr)) {
            return {
                selections: {
                    nl: coerceCityList(parsed.nl, cityLookup),
                    tr: coerceCityList(parsed.tr, cityLookup),
                },
                labels: normalizeLabelMap(parsed.labels),
            };
        }
        if (
            typeof parsed === "object" &&
            Array.isArray(parsed.selections?.nl) &&
            Array.isArray(parsed.selections?.tr)
        ) {
            return {
                selections: {
                    nl: coerceCityList(parsed.selections.nl, cityLookup),
                    tr: coerceCityList(parsed.selections.tr, cityLookup),
                },
                labels: normalizeLabelMap(parsed.labels),
            };
        }
        return null;
    } catch {
        return null;
    }
}

function buildDefaultPreferences(config: NewsCityList | null, lookup?: CityLookup): CityPreferences {
    if (!config) {
        return { nl: [], tr: [] };
    }
    const derive = (country: CountryCode) => {
        const defaults = config.defaults[country] ?? [];
        const canonical = defaults
            .map((key) => canonicalizeCityKey(key, lookup))
            .filter((key): key is string => Boolean(key));
        if (canonical.length >= MAX_SELECTIONS) {
            return canonical.slice(0, MAX_SELECTIONS);
        }
        const fallback = config.cities
            .filter((city) => city.country === country)
            .slice(0, MAX_SELECTIONS)
            .map((city) => city.cityKey);
        const merged = [...canonical, ...fallback];
        return merged.slice(0, MAX_SELECTIONS);
    };
    return {
        nl: derive("nl"),
        tr: derive("tr"),
    };
}

function coerceCityList(values: string[], cityLookup?: CityLookup): string[] {
    const normalized: string[] = [];
    const seen = new Set<string>();
    for (const value of values) {
        if (typeof value !== "string") continue;
        const candidate = canonicalizeCityKey(value, cityLookup);
        if (!candidate || seen.has(candidate)) continue;
        seen.add(candidate);
        normalized.push(candidate);
        if (normalized.length === MAX_SELECTIONS) break;
    }
    return normalized;
}

function toCityLabelFromNewsCity(city: NewsCity): CityLabel | null {
    const key = normalizeCityKey(city.cityKey);
    if (!key) return null;
    return {
        key,
        name: city.name,
        country: city.country,
        province: city.province ?? undefined,
    };
}

function normalizeLabelMap(map?: CityLabelMap | null): CityLabelMap {
    if (!map) return {};
    const result: CityLabelMap = {};
    Object.values(map).forEach((label) => {
        const key = normalizeCityKey(label.key);
        if (!key) {
            return;
        }
        result[key] = {
            key,
            name: label.name,
            country: label.country,
            province: label.province,
        };
    });
    return result;
}

function normalizeCityKey(value?: string): string {
    return (value ?? "").trim().toLowerCase();
}

function canonicalizeCityKey(value: string, cityLookup?: CityLookup): string | null {
    const normalized = normalizeCityKey(value);
    if (!normalized) return null;
    const match = cityLookup?.[normalized];
    return match ? match.cityKey : normalized;
}

function buildCityLookup(config: NewsCityList | null): CityLookup {
    if (!config) return {};
    const lookup: CityLookup = {};
    config.cities.forEach((city) => {
        lookup[city.cityKey] = city;
        if (city.legacyKey) {
            lookup[city.legacyKey] = city;
        }
    });
    return lookup;
}

function deriveRecommendations(config: NewsCityList | null): CityRecommendations | null {
    if (!config) return null;
    const byKey = new Map<string, NewsCity>();
    config.cities.forEach((city) => {
        byKey.set(city.cityKey, city);
    });
    const build = (country: CountryCode) => {
        const defaultKeys = config.defaults[country] ?? [];
        const defaults = defaultKeys
            .map((key) => byKey.get(key))
            .filter((city): city is NewsCity => Boolean(city));
        if (defaults.length) {
            return defaults;
        }
        return config.cities.filter((city) => city.country === country).slice(0, MAX_SELECTIONS);
    };
    return {
        nl: build("nl"),
        tr: build("tr"),
    };
}

