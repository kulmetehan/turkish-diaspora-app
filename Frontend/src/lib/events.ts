// Frontend/src/lib/events.ts

// === Typen ===
export type MapSelectDetail = { id: number };
export type ListHighlightDetail = { id: number };

// === Event namen (één bron van waarheid) ===
const EVT_MAP_SELECT = "tda:map/select";           // lijst -> kaart
const EVT_LIST_HIGHLIGHT = "tda:list/highlight";   // kaart -> lijst

// === Zenden ===
export function emitMapSelect(id: number) {
  window.dispatchEvent(new CustomEvent<MapSelectDetail>(EVT_MAP_SELECT, { detail: { id } }));
}

export function emitListHighlight(id: number) {
  window.dispatchEvent(new CustomEvent<ListHighlightDetail>(EVT_LIST_HIGHLIGHT, { detail: { id } }));
}

// === Luisteren (geeft unsubscribe terug) ===
export function onMapSelect(handler: (id: number) => void): () => void {
  const fn = (e: Event) => {
    const d = (e as CustomEvent<MapSelectDetail>).detail;
    if (d?.id) handler(d.id);
  };
  window.addEventListener(EVT_MAP_SELECT, fn);
  return () => window.removeEventListener(EVT_MAP_SELECT, fn);
}

export function onListHighlight(handler: (id: number) => void): () => void {
  const fn = (e: Event) => {
    const d = (e as CustomEvent<ListHighlightDetail>).detail;
    if (d?.id) handler(d.id);
  };
  window.addEventListener(EVT_LIST_HIGHLIGHT, fn);
  return () => window.removeEventListener(EVT_LIST_HIGHLIGHT, fn);
}
