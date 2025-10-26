// Frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";

import "leaflet/dist/leaflet.css";
import "mapbox-gl/dist/mapbox-gl.css";
import App from "./App";
import "./index.css";

import RequireAdmin from "@/components/auth/RequireAdmin";
import { Header } from "@/components/Header";
import { Toaster } from "@/components/ui/toaster";
import { initTheme } from "@/lib/theme/darkMode";
import AdminHomePage from "@/pages/AdminHomePage";
import LoginPage from "@/pages/LoginPage";
import UiKit from "@/pages/UiKit";

// Vite levert dit via 'base' (bv. "/turkish-diaspora-app/") voor GitHub Pages builds.

initTheme();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <Header />
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/ui-kit" element={<UiKit />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin" element={<RequireAdmin><AdminHomePage /></RequireAdmin>} />
        {/* Catch-all naar home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </HashRouter>
  </React.StrictMode>
);