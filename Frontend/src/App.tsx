import { useEffect, useState } from "react";
import MapView from "./components/MapView";
import { API_BASE_URL, getHealth } from "./lib/api";

export default function App() {
  const [health, setHealth] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getHealth();
        setHealth(data?.status ?? null);
      } catch {
        setHealth(null);
      }
    })();
  }, []);

  return (
    <div className="min-h-screen w-full" style={{ fontFamily: "system-ui, Arial, sans-serif" }}>
      {/* Full-bleed Map */}
      <div style={{ height: "65vh", width: "100%" }}>
        <MapView />
      </div>

      {/* Info blok */}
      <div style={{ padding: 24 }}>
        <h1>Turkish Diaspora App</h1>
        <p>Kaart + lijst experience (Epic 4) — TDA-13 in uitvoering.</p>

        <hr style={{ margin: "16px 0" }} />

        <h2>Config</h2>
        <p>
          <strong>API base URL:</strong> {API_BASE_URL || "(not set)"}
        </p>

        <h2>Backend health</h2>
        <p>
          {health === null
            ? "Proberen te verbinden… (of backend niet bereikbaar)"
            : `Backend zegt: ${health}`}
        </p>
      </div>
    </div>
  );
}
