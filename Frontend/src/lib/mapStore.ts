
let _map: mapboxgl.Map | null = null;

export function getMap(): mapboxgl.Map | null {
    return _map;
}

export function setMap(m: mapboxgl.Map): void {
    if (_map && m !== _map) {
        // eslint-disable-next-line no-console
        console.warn("[MapStore] attempted to replace existing Mapbox map instance");
        return;
    }
    _map = m;
}

export function ensureDebugId(map: mapboxgl.Map): string {
    const anyMap = map as any;
    if (!anyMap.__TDA_DEBUG_ID) {
        const id = (globalThis.crypto && (crypto as any).randomUUID?.()) || String(Date.now());
        anyMap.__TDA_DEBUG_ID = id;
    }
    return String(anyMap.__TDA_DEBUG_ID);
}



