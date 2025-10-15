// Frontend/src/main.tsx

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// App styles
import "./App.css";

// BELANGRIJK: Leaflet basis-styles (tiles, controls, popups, etc.)
import "leaflet/dist/leaflet.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
