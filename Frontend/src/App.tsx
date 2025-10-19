// Frontend/src/App.tsx

import "./App.css";

import Filters from "./components/Filters";
import SortBar from "./components/SortBar";
import LocationList from "./components/LocationList";
import MapView from "./components/MapView";

import { useLocations } from "./hooks/useLocations";

function App() {
  const { locations, categories, isLoading, error } = useLocations();

  return (
    <div
      className={[
        // behoud je eigen styles
        "app-layout",
        // responsive shell
        "mx-auto max-w-7xl p-4 md:p-6",
        "grid gap-4 md:grid-cols-[380px,1fr]"
      ].join(" ")}
    >
      <aside
        className={[
          "app-sidebar",
          "space-y-4"
        ].join(" ")}
        aria-label="Filter en resultaten"
      >
        <div
          className={[
            "toolbar",
            "flex flex-wrap items-center gap-2 md:gap-3"
          ].join(" ")}
        >
          <Filters categories={categories} />
          <SortBar />
        </div>

        {isLoading && (
          <div className="loading text-sm text-muted-foreground">Laden…</div>
        )}
        {error && (
          <div className="error text-sm text-destructive-foreground">
            Fout bij laden: {error}
          </div>
        )}

        {!isLoading && !error && (
          <LocationList
            locations={locations}
            autoScrollToSelected
            emptyText="Geen resultaten. Pas je filters aan."
          />
        )}
      </aside>

      <main
        className={[
          "app-map",
          "min-h-[60vh] md:min-h-[80vh]"
        ].join(" ")}
        aria-label="Kaart"
      >
        <MapView locations={locations} />
      </main>
    </div>
  );
}

export default App;
