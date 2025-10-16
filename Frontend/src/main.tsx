// Frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import App from "./App";
import AdminPage from "./pages/AdminPage"; // <-- if you don't have this, remove the /admin route

import "./App.css";
import "leaflet/dist/leaflet.css";

// On GitHub Pages we’re served under /turkish-diaspora-app
// The workflow sets GITHUB_PAGES=true during build
const isPages = !!import.meta.env.GITHUB_PAGES;
const basename = isPages ? "/turkish-diaspora-app" : "/";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <Routes>
        {/* Public app at root */}
        <Route path="/" element={<App />} />

        {/* Optional admin page (remove if you don't have it yet) */}
        <Route path="/admin" element={<AdminPage />} />

        {/* Catch-all: send unknown paths to root */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
