import type { KnownCity } from "@/lib/cityResolver";

export const KNOWN_CITIES: KnownCity[] = [
    { name: "Rotterdam", lat: 51.9244, lng: 4.4777 },
    { name: "Den Haag", lat: 52.0705, lng: 4.3007 },
    { name: "Delft", lat: 52.0116, lng: 4.3571 },
    { name: "Schiedam", lat: 51.9192, lng: 4.3881 },
    { name: "Vlaardingen", lat: 51.9129, lng: 4.3410 },
    { name: "Dordrecht", lat: 51.8133, lng: 4.6901 },
    // TODO: Extend with additional coverage cities as discovery expands.
];

