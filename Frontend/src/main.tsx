// Frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import App from "./App";
import "./index.css";
import "leaflet/dist/leaflet.css";

import UiKit from "@/pages/UiKit";
import { Header } from "@/components/Header";
import { Toaster } from "@/components/ui/toaster";
import { initTheme } from "@/lib/theme/darkMode";

// Vite levert dit via 'base' (bv. "/turkish-diaspora-app/") voor GitHub Pages builds.
const basename = import.meta.env.BASE_URL || "/";

initTheme();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <Header />
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/ui-kit" element={<UiKit />} />
        {/* Catch-all naar home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </BrowserRouter>
  </React.StrictMode>
);
