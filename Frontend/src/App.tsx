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
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="toolbar">
          <Filters categories={categories} />
          <SortBar />
        </div>

        {isLoading && <div className="loading">Laden…</div>}
        {error && <div className="error">Fout bij laden: {error}</div>}

        {!isLoading && !error && (
          <LocationList
            locations={locations}
            autoScrollToSelected
            emptyText="Geen resultaten. Pas je filters aan."
          />
        )}
      </aside>

      <main className="app-map">
        {/* MapView ontvangt de *zelfde* dataset -> geen tweede fetch */}
        <MapView locations={locations} />
      </main>
    </div>
  );
}

export default App;
