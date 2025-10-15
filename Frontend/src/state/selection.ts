// Frontend/src/state/selection.ts
//
// Back-compat shim naar de centrale UI store.
// Alles hier is een dunne doorverwijzing zodat bestaande imports blijven werken.

import {
  useSelectedLocationId as useSelectedLocationIdFromUI,
  selectLocation as selectLocationInUI,
} from "./ui";

/** Huidige geselecteerde locatie-id (list <-> map sync). */
export const useSelectedLocationId = useSelectedLocationIdFromUI;

/** Stel de geselecteerde locatie in (of null om te deselecteren). */
export function selectLocation(id: string | null) {
  selectLocationInUI(id);
}
